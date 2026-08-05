import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useResourceLoading from "./useResourceLoading";


const api = vi.hoisted(() => ({ fetchResourceLoading: vi.fn() }));
vi.mock("../services/api", () => api);

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function props(overrides = {}) {
  return { projectId: 7, enabled: true, reportRequestError: vi.fn(), ...overrides };
}

describe("useResourceLoading", () => {
  beforeEach(() => api.fetchResourceLoading.mockReset());

  it("loads on demand and deduplicates an active equivalent request", async () => {
    const pending = deferred();
    api.fetchResourceLoading.mockReturnValue(pending.promise);
    const { result } = renderHook(() => useResourceLoading(props()));
    let first;
    act(() => {
      first = result.current.load({ startDate: "2026-08-10" });
      void result.current.load({ startDate: "2026-08-10" });
    });
    expect(api.fetchResourceLoading).toHaveBeenCalledOnce();
    await act(async () => {
      pending.resolve({ project_id: 7, resources: [] });
      await first;
    });
    expect(result.current.data.project_id).toBe(7);
  });

  it("clears stale metrics on project switch", async () => {
    const old = deferred();
    api.fetchResourceLoading
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce({ project_id: 8, resources: [] });
    const { result, rerender } = renderHook(
      ({ projectId }) => useResourceLoading(props({ projectId })),
      { initialProps: { projectId: 7 } }
    );
    act(() => { void result.current.load(); });
    rerender({ projectId: 8 });
    expect(result.current.data).toBeNull();
    await act(async () => result.current.load());
    await act(async () => old.resolve({ project_id: 7, resources: [{ id: 1 }] }));
    expect(result.current.data.project_id).toBe(8);
  });

  it("reports failures without retaining loading data", async () => {
    const error = new Error("offline");
    const reportRequestError = vi.fn();
    api.fetchResourceLoading.mockRejectedValueOnce(error);
    const { result } = renderHook(() => useResourceLoading(props({ reportRequestError })));
    await act(async () => {
      expect(await result.current.load()).toBeNull();
    });
    expect(result.current.error).toBe(error);
    expect(result.current.data).toBeNull();
    expect(reportRequestError).toHaveBeenCalledWith("Unable to load resource loading", error);
  });
});
