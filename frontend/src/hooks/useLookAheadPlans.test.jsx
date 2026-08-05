import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useLookAheadPlans from "./useLookAheadPlans";


const api = vi.hoisted(() => ({
  archiveLookAheadPlan: vi.fn(),
  createLookAheadPlan: vi.fn(),
  getLookAheadPlan: vi.fn(),
  listLookAheadPlans: vi.fn(),
  updateLookAheadItem: vi.fn(),
  updateLookAheadPlan: vi.fn(),
}));

vi.mock("../services/api", () => api);


const plans = [
  { id: 2, project_id: 7, name: "Latest", status: "active" },
  { id: 1, project_id: 7, name: "Archived", status: "archived" },
];

const detail = (id) => ({ plan: plans.find((plan) => plan.id === id), weeks: [] });

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function props(overrides = {}) {
  return {
    projectId: 7,
    enabled: true,
    showNotice: vi.fn(),
    reportRequestError: vi.fn(),
    ...overrides,
  };
}

describe("useLookAheadPlans", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.listLookAheadPlans.mockResolvedValue({ plans, total: 2 });
    api.getLookAheadPlan.mockImplementation((_projectId, planId) =>
      Promise.resolve(detail(planId))
    );
  });

  it("loads plans and selects the newest active plan", async () => {
    const { result } = renderHook(() => useLookAheadPlans(props()));

    await waitFor(() => expect(result.current.detail?.plan.id).toBe(2));
    expect(result.current.selectedPlanId).toBe(2);
    expect(api.listLookAheadPlans).toHaveBeenCalledOnce();
    expect(api.getLookAheadPlan).toHaveBeenCalledWith(
      7,
      2,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("clears stale project state and ignores the old response", async () => {
    const first = deferred();
    api.listLookAheadPlans
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({
        plans: [{ id: 8, project_id: 8, name: "Other", status: "active" }],
      });
    api.getLookAheadPlan.mockResolvedValue({
      plan: { id: 8, project_id: 8, name: "Other", status: "active" },
      weeks: [],
    });
    const { result, rerender } = renderHook(
      ({ projectId }) => useLookAheadPlans(props({ projectId })),
      { initialProps: { projectId: 7 } }
    );

    await waitFor(() => expect(api.listLookAheadPlans).toHaveBeenCalledOnce());
    rerender({ projectId: 8 });
    await waitFor(() => expect(result.current.detail?.plan.id).toBe(8));
    await act(async () => first.resolve({ plans }));
    expect(result.current.projectId).toBe(8);
    expect(result.current.selectedPlanId).toBe(8);
  });

  it("rejects stale plan detail after selection changes", async () => {
    const latest = deferred();
    api.getLookAheadPlan
      .mockReturnValueOnce(latest.promise)
      .mockResolvedValueOnce(detail(1));
    const { result } = renderHook(() => useLookAheadPlans(props()));

    await waitFor(() => expect(result.current.selectedPlanId).toBe(2));
    await act(async () => result.current.selectPlan(1));
    expect(result.current.detail.plan.id).toBe(1);
    await act(async () => latest.resolve(detail(2)));
    expect(result.current.detail.plan.id).toBe(1);
  });

  it("deduplicates create and updates detail after item mutation", async () => {
    const creation = deferred();
    api.createLookAheadPlan.mockReturnValue(creation.promise);
    api.updateLookAheadItem.mockResolvedValue({ plan: plans[0], weeks: [] });
    const showNotice = vi.fn();
    const { result } = renderHook(() =>
      useLookAheadPlans(props({ showNotice }))
    );
    await waitFor(() => expect(result.current.detail?.plan.id).toBe(2));

    let first;
    act(() => {
      first = result.current.createPlan({ name: "New" });
      void result.current.createPlan({ name: "Duplicate click" });
    });
    expect(api.createLookAheadPlan).toHaveBeenCalledOnce();
    await act(async () => {
      creation.resolve({
        plan: { id: 3, project_id: 7, name: "New", status: "active" },
      });
      await first;
    });
    expect(result.current.selectedPlanId).toBe(3);

    await act(async () =>
      result.current.updateItem(3, 9, { readiness_status: "ready" })
    );
    expect(api.updateLookAheadItem).toHaveBeenCalledWith(
      7,
      3,
      9,
      { readiness_status: "ready" },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(showNotice).toHaveBeenCalledWith(
      "success",
      "Look-ahead item updated."
    );
  });
});
