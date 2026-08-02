import { StrictMode } from "react";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useDocumentSearch from "./useDocumentSearch";
import { INITIAL_DOCUMENT_SEARCH_FILTERS } from "../utils/documentSearch";


const apiMocks = vi.hoisted(() => ({
  searchProjectDocuments: vi.fn(),
}));
vi.mock("../services/api", () => apiMocks);


const RESULT = {
  project_id: 1,
  query: "sprinkler",
  scope: "all",
  results: [{ document_id: 10 }],
  pagination: { limit: 20, offset: 0, total: 1, has_more: false },
};


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}


describe("useDocumentSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.searchProjectDocuments.mockResolvedValue(RESULT);
  });

  it("does not request until submit and submits one bounded search in Strict Mode", async () => {
    const { result } = renderHook(
      () => useDocumentSearch({ projectId: 1 }),
      { wrapper: StrictMode }
    );
    expect(apiMocks.searchProjectDocuments).not.toHaveBeenCalled();

    await act(async () => {
      await result.current.submit(" sprinkler ", {
        ...INITIAL_DOCUMENT_SEARCH_FILTERS,
        scope: "documents",
      });
    });

    expect(apiMocks.searchProjectDocuments).toHaveBeenCalledTimes(1);
    expect(apiMocks.searchProjectDocuments).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        query: "sprinkler",
        scope: "documents",
        limit: 20,
        offset: 0,
        signal: expect.any(AbortSignal),
      })
    );
    expect(result.current.data).toEqual(RESULT);
  });

  it("clears stale data and aborts on project change", async () => {
    const pending = deferred();
    apiMocks.searchProjectDocuments.mockReturnValue(pending.promise);
    const hook = renderHook(
      ({ projectId }) => useDocumentSearch({ projectId }),
      { initialProps: { projectId: 1 } }
    );
    act(() => {
      void hook.result.current.submit(
        "sprinkler",
        INITIAL_DOCUMENT_SEARCH_FILTERS
      );
    });
    const signal = apiMocks.searchProjectDocuments.mock.calls[0][1].signal;
    hook.rerender({ projectId: 2 });

    expect(signal.aborted).toBe(true);
    expect(hook.result.current.data).toBeNull();
    expect(hook.result.current.isLoading).toBe(false);
    await act(async () => {
      pending.resolve(RESULT);
      await pending.promise;
    });
    expect(hook.result.current.data).toBeNull();
  });

  it("reports errors, retries, paginates, and clears", async () => {
    const error = Object.assign(new Error("Search limited"), { status: 429 });
    const onError = vi.fn();
    apiMocks.searchProjectDocuments
      .mockRejectedValueOnce(error)
      .mockResolvedValueOnce(RESULT)
      .mockResolvedValueOnce({
        ...RESULT,
        pagination: { ...RESULT.pagination, offset: 20 },
      });
    const { result } = renderHook(() =>
      useDocumentSearch({ projectId: 1, onError })
    );

    await act(async () => {
      await result.current.submit(
        "sprinkler",
        INITIAL_DOCUMENT_SEARCH_FILTERS
      );
    });
    expect(result.current.error).toBe(error);
    expect(onError).toHaveBeenCalledWith(
      "Unable to search project documents",
      error
    );

    await act(async () => {
      await result.current.retry();
    });
    expect(result.current.data).toEqual(RESULT);

    await act(async () => {
      await result.current.goToOffset(20);
    });
    expect(apiMocks.searchProjectDocuments).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({ offset: 20 })
    );
    act(() => result.current.clear());
    expect(result.current.data).toBeNull();
    expect(result.current.request).toBeNull();
  });

  it("ignores an older response after a newer submit", async () => {
    const first = deferred();
    const second = deferred();
    apiMocks.searchProjectDocuments
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { result } = renderHook(() => useDocumentSearch({ projectId: 1 }));
    act(() => {
      void result.current.submit("first", INITIAL_DOCUMENT_SEARCH_FILTERS);
      void result.current.submit("second", INITIAL_DOCUMENT_SEARCH_FILTERS);
    });
    await act(async () => {
      second.resolve({ ...RESULT, query: "second" });
      await second.promise;
    });
    expect(result.current.data.query).toBe("second");
    await act(async () => {
      first.resolve({ ...RESULT, query: "first" });
      await first.promise;
    });
    expect(result.current.data.query).toBe("second");
  });
});
