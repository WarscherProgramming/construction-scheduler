import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useScheduleHealth from "./useScheduleHealth";


const api = vi.hoisted(() => ({ fetchScheduleHealth: vi.fn() }));
vi.mock("../services/api", () => api);

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function props(overrides = {}) {
  return { projectId: 7, enabled: true, onError: vi.fn(), ...overrides };
}

describe("useScheduleHealth", () => {
  beforeEach(() => api.fetchScheduleHealth.mockReset());

  it("loads once and deduplicates an active request", async () => {
    const pending = deferred();
    api.fetchScheduleHealth.mockReturnValue(pending.promise);
    const { result } = renderHook(() => useScheduleHealth(props()));

    await waitFor(() => expect(api.fetchScheduleHealth).toHaveBeenCalledOnce());
    let retry;
    act(() => { retry = result.current.retry(); });
    expect(api.fetchScheduleHealth).toHaveBeenCalledOnce();

    await act(async () => {
      pending.resolve({ category: "stable" });
      await retry;
    });
    expect(result.current.health.category).toBe("stable");
  });

  it("clears old health and rejects a stale response after project switch", async () => {
    const first = deferred();
    const second = deferred();
    api.fetchScheduleHealth
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { result, rerender } = renderHook(
      ({ projectId }) => useScheduleHealth(props({ projectId })),
      { initialProps: { projectId: 7 } }
    );
    await waitFor(() => expect(api.fetchScheduleHealth).toHaveBeenCalledOnce());

    rerender({ projectId: 8 });
    expect(result.current.health).toBeNull();
    await waitFor(() => expect(api.fetchScheduleHealth).toHaveBeenCalledTimes(2));
    await act(async () => second.resolve({ category: "attention" }));
    await act(async () => first.resolve({ category: "critical" }));

    expect(result.current.health.category).toBe("attention");
  });

  it("reports current failures and supports retry", async () => {
    const error = new Error("offline");
    const onError = vi.fn();
    api.fetchScheduleHealth
      .mockRejectedValueOnce(error)
      .mockResolvedValueOnce({ category: "stable" });
    const { result } = renderHook(() => useScheduleHealth(props({ onError })));

    await waitFor(() => expect(result.current.error).toBe(error));
    expect(onError).toHaveBeenCalledWith("Unable to load schedule health", error);
    await act(async () => result.current.retry());
    expect(result.current.health.category).toBe("stable");
  });
});
