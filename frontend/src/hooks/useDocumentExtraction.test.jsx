import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useDocumentExtraction from "./useDocumentExtraction";


const apiMocks = vi.hoisted(() => ({
  getDocumentExtraction: vi.fn(),
  reprocessDocumentExtraction: vi.fn(),
}));
vi.mock("../services/api", () => apiMocks);


const COMPLETED = {
  status: "completed",
  extraction_method: "embedded_text",
  searchable: true,
  retry_eligible: true,
};
const PENDING = {
  ...COMPLETED,
  status: "pending",
  searchable: true,
  retry_eligible: false,
};


function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}


describe("useDocumentExtraction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getDocumentExtraction.mockResolvedValue({ extraction: COMPLETED });
    apiMocks.reprocessDocumentExtraction.mockResolvedValue({
      extraction: PENDING,
    });
  });

  it("uses a bundled explorer summary without an extra request", () => {
    const { result } = renderHook(() =>
      useDocumentExtraction({
        projectId: 1,
        documentId: 8,
        initialExtraction: COMPLETED,
        load: false,
      })
    );
    expect(result.current.extraction).toEqual(COMPLETED);
    expect(apiMocks.getDocumentExtraction).not.toHaveBeenCalled();
  });

  it("loads one exact status under Strict Mode", async () => {
    const { result } = renderHook(
      () =>
        useDocumentExtraction({
          projectId: 1,
          documentId: 8,
          load: true,
        }),
      { wrapper: StrictMode }
    );
    await waitFor(() => expect(result.current.extraction).toEqual(COMPLETED));
    expect(apiMocks.getDocumentExtraction).toHaveBeenCalledTimes(1);
    expect(apiMocks.getDocumentExtraction).toHaveBeenCalledWith(
      1,
      8,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("clears stale revision state on identity changes", async () => {
    const first = deferred();
    apiMocks.getDocumentExtraction
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ extraction: PENDING });
    const hook = renderHook(
      ({ documentId }) =>
        useDocumentExtraction({ projectId: 1, documentId, load: true }),
      { initialProps: { documentId: 8 } }
    );
    await waitFor(() =>
      expect(apiMocks.getDocumentExtraction).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ documentId: 9 });
    expect(hook.result.current.extraction).toBeNull();
    await waitFor(() => expect(hook.result.current.extraction).toEqual(PENDING));
    await act(async () => {
      first.resolve({ extraction: COMPLETED });
      await first.promise;
    });
    expect(hook.result.current.extraction).toEqual(PENDING);
  });

  it("queues reprocessing and reports safe failures", async () => {
    const onUpdate = vi.fn();
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useDocumentExtraction({
        projectId: 1,
        documentId: 8,
        initialExtraction: COMPLETED,
        load: false,
        onUpdate,
        onError,
      })
    );
    await act(async () => {
      expect(await result.current.reprocess()).toBe(true);
    });
    expect(result.current.extraction).toEqual(PENDING);
    expect(onUpdate).toHaveBeenCalledWith(PENDING);

    const error = Object.assign(new Error("Too many requests"), { status: 429 });
    apiMocks.reprocessDocumentExtraction.mockRejectedValueOnce(error);
    await act(async () => {
      expect(await result.current.reprocess()).toBe(false);
    });
    expect(result.current.error).toBe(error);
    expect(onError).toHaveBeenCalledWith(
      "Unable to reprocess document text",
      error
    );
  });
});
