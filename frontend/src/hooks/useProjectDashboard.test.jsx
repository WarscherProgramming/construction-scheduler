import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import useProjectDashboard from "./useProjectDashboard";


const apiMocks = vi.hoisted(() => ({
  fetchProjectDashboard: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const DATE_FACTORY = () => new Date(2026, 6, 27, 23, 30);
const DASHBOARD = {
  as_of: "2026-07-27",
  project: { id: 1, name: "Riverside" },
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


describe("useProjectDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.fetchProjectDashboard.mockResolvedValue(DASHBOARD);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not request a dashboard without a project", () => {
    const { result } = renderHook(() =>
      useProjectDashboard({
        projectId: null,
        dateFactory: DATE_FACTORY,
      })
    );

    expect(result.current.dashboard).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(apiMocks.fetchProjectDashboard).not.toHaveBeenCalled();
  });

  it("deduplicates the initial in-flight request under Strict Mode", async () => {
    const pending = deferred();
    apiMocks.fetchProjectDashboard.mockReturnValue(pending.promise);

    const { result } = renderHook(
      () =>
        useProjectDashboard({
          projectId: 1,
          dateFactory: DATE_FACTORY,
        }),
      { wrapper: StrictMode }
    );

    expect(result.current.asOf).toBe("2026-07-27");
    expect(result.current.isLoading).toBe(true);
    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );

    await act(async () => {
      pending.resolve(DASHBOARD);
      await pending.promise;
    });
    await waitFor(() => expect(result.current.dashboard).toEqual(DASHBOARD));
  });

  it("exposes a retryable failure and retry creates a fresh request", async () => {
    const onError = vi.fn();
    apiMocks.fetchProjectDashboard
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce(DASHBOARD);
    const { result } = renderHook(() =>
      useProjectDashboard({
        projectId: 1,
        dateFactory: DATE_FACTORY,
        onError,
      })
    );

    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.dashboard).toBeNull();
    expect(onError).toHaveBeenCalledOnce();

    act(() => result.current.retry());

    await waitFor(() => expect(result.current.dashboard).toEqual(DASHBOARD));
    expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(2);
  });

  it("aborts a superseded request and clears old project data", async () => {
    const first = deferred();
    apiMocks.fetchProjectDashboard
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({
        ...DASHBOARD,
        project: { id: 2, name: "North Ridge" },
      });
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    const firstSignal =
      apiMocks.fetchProjectDashboard.mock.calls[0][2].signal;

    hook.rerender({ projectId: 2 });

    expect(hook.result.current.dashboard).toBeNull();
    expect(hook.result.current.isLoading).toBe(true);
    expect(firstSignal.aborted).toBe(true);
    await waitFor(() =>
      expect(hook.result.current.dashboard?.project.id).toBe(2)
    );
  });

  it("hides a loaded project's lists while the next project loads", async () => {
    const second = deferred();
    apiMocks.fetchProjectDashboard
      .mockResolvedValueOnce({
        ...DASHBOARD,
        attention_items: [{ record_id: 1, title: "Old attention" }],
        upcoming_tasks: [{ id: 1, name: "Old task" }],
      })
      .mockReturnValueOnce(second.promise);
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(hook.result.current.dashboard?.project.id).toBe(1)
    );

    hook.rerender({ projectId: 2 });

    expect(hook.result.current.dashboard).toBeNull();
    expect(hook.result.current.isLoading).toBe(true);
    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(2)
    );
  });

  it("ignores stale and intentionally aborted request results", async () => {
    const first = deferred();
    const second = deferred();
    const onError = vi.fn();
    apiMocks.fetchProjectDashboard
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
          onError,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ projectId: 2 });
    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(2)
    );

    await act(async () => {
      second.resolve({
        ...DASHBOARD,
        project: { id: 2, name: "North Ridge" },
      });
      await second.promise;
    });
    await act(async () => {
      first.resolve(DASHBOARD);
      await first.promise;
    });

    expect(hook.result.current.dashboard.project.id).toBe(2);
    expect(onError).not.toHaveBeenCalled();
  });

  it("rejects an old response after an A to B to A project switch", async () => {
    const firstProjectA = deferred();
    const currentProjectA = deferred();
    apiMocks.fetchProjectDashboard
      .mockReturnValueOnce(firstProjectA.promise)
      .mockResolvedValueOnce({
        ...DASHBOARD,
        project: { id: 2, name: "North Ridge" },
      })
      .mockReturnValueOnce(currentProjectA.promise);
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ projectId: 2 });
    await waitFor(() =>
      expect(hook.result.current.dashboard?.project.id).toBe(2)
    );
    hook.rerender({ projectId: 1 });
    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(3)
    );

    await act(async () => {
      firstProjectA.resolve({
        ...DASHBOARD,
        project: { id: 1, name: "Stale Riverside" },
      });
      await firstProjectA.promise;
    });
    expect(hook.result.current.dashboard).toBeNull();
    expect(hook.result.current.isLoading).toBe(true);

    await act(async () => {
      currentProjectA.resolve({
        ...DASHBOARD,
        project: { id: 1, name: "Current Riverside" },
      });
      await currentProjectA.promise;
    });
    expect(hook.result.current.dashboard?.project.name).toBe(
      "Current Riverside"
    );
  });

  it("ignores an old project rejection after the next project succeeds", async () => {
    const first = deferred();
    const onError = vi.fn();
    apiMocks.fetchProjectDashboard
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({
        ...DASHBOARD,
        project: { id: 2, name: "North Ridge" },
      });
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
          onError,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ projectId: 2 });
    await waitFor(() =>
      expect(hook.result.current.dashboard?.project.id).toBe(2)
    );

    await act(async () => {
      first.reject(new Error("Old project failed"));
      await first.promise.catch(() => {});
    });

    expect(hook.result.current.dashboard?.project.id).toBe(2);
    expect(hook.result.current.error).toBeNull();
    expect(onError).not.toHaveBeenCalled();
  });

  it("coalesces rapid retries and allows a fresh request after success", async () => {
    const recovered = deferred();
    apiMocks.fetchProjectDashboard
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockReturnValueOnce(recovered.promise)
      .mockResolvedValueOnce({
        ...DASHBOARD,
        project: { id: 1, name: "Refreshed Riverside" },
      });
    const { result } = renderHook(() =>
      useProjectDashboard({
        projectId: 1,
        dateFactory: DATE_FACTORY,
      })
    );

    await waitFor(() => expect(result.current.error).toBeTruthy());
    act(() => {
      result.current.retry();
      result.current.retry();
    });
    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(2)
    );

    await act(async () => {
      recovered.resolve(DASHBOARD);
      await recovered.promise;
    });
    await waitFor(() => expect(result.current.dashboard).toEqual(DASHBOARD));

    act(() => result.current.retry());
    await waitFor(() =>
      expect(result.current.dashboard?.project.name).toBe(
        "Refreshed Riverside"
      )
    );
    expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(3);
  });

  it("clears state when project selection is removed", async () => {
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
        }),
      { initialProps: { projectId: null } }
    );

    expect(hook.result.current.isLoading).toBe(false);
    hook.rerender({ projectId: 1 });
    await waitFor(() =>
      expect(hook.result.current.dashboard).toEqual(DASHBOARD)
    );

    hook.rerender({ projectId: null });
    expect(hook.result.current.dashboard).toBeNull();
    expect(hook.result.current.error).toBeNull();
    expect(hook.result.current.isLoading).toBe(false);
    expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledOnce();
  });

  it("does not expose or report an AbortError", async () => {
    const onError = vi.fn();
    apiMocks.fetchProjectDashboard
      .mockImplementationOnce((projectId, asOf, { signal }) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      })
      .mockResolvedValueOnce({
        ...DASHBOARD,
        project: { id: 2, name: "North Ridge" },
      });
    const hook = renderHook(
      ({ projectId }) =>
        useProjectDashboard({
          projectId,
          dateFactory: DATE_FACTORY,
          onError,
        }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ projectId: 2 });

    await waitFor(() =>
      expect(hook.result.current.dashboard?.project.id).toBe(2)
    );
    expect(hook.result.current.error).toBeNull();
    expect(onError).not.toHaveBeenCalled();
  });

  it("aborts pending work on unmount", async () => {
    const pending = deferred();
    apiMocks.fetchProjectDashboard.mockReturnValue(pending.promise);
    const hook = renderHook(() =>
      useProjectDashboard({
        projectId: 1,
        dateFactory: DATE_FACTORY,
      })
    );

    await waitFor(() =>
      expect(apiMocks.fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    const signal = apiMocks.fetchProjectDashboard.mock.calls[0][2].signal;

    hook.unmount();

    expect(signal.aborted).toBe(true);
  });
});
