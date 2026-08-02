import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useScheduleBaselines from "./useScheduleBaselines";


const apiMocks = vi.hoisted(() => ({
  archiveScheduleBaseline: vi.fn(),
  createScheduleBaseline: vi.fn(),
  fetchScheduleVariance: vi.fn(),
  listScheduleBaselines: vi.fn(),
  selectScheduleBaseline: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const ACTIVE = {
  id: 10,
  project_id: 1,
  name: "Issued Plan",
  status: "active",
  captured_at: "2026-08-02T16:00:00Z",
};
const ARCHIVED = {
  ...ACTIVE,
  id: 9,
  name: "Bid Plan",
  status: "archived",
};
const LIST = {
  baselines: [ACTIVE, ARCHIVED],
  comparison_baseline_id: 10,
  total: 2,
  limit: 100,
  offset: 0,
};
const VARIANCE = {
  baseline: ACTIVE,
  summary: { baseline_id: 10, slipped_count: 1 },
  tasks: [{ task_id: 1, name: "Excavate" }],
  total: 1,
  limit: 50,
  offset: 0,
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


function renderBaselines(props = {}, options = {}) {
  const defaults = {
    projectId: 1,
    enabled: true,
    setScheduleSettings: vi.fn(),
    showNotice: vi.fn(),
    reportRequestError: vi.fn(),
  };
  return renderHook(
    (currentProps) =>
      useScheduleBaselines({ ...defaults, ...currentProps }),
    { initialProps: props, ...options }
  );
}


describe("useScheduleBaselines", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listScheduleBaselines.mockResolvedValue(LIST);
    apiMocks.fetchScheduleVariance.mockResolvedValue(VARIANCE);
    apiMocks.createScheduleBaseline.mockResolvedValue({
      baseline: ACTIVE,
      comparison_baseline_id: 10,
    });
    apiMocks.archiveScheduleBaseline.mockResolvedValue({
      baseline: { ...ACTIVE, status: "archived" },
      comparison_baseline_id: null,
    });
    apiMocks.selectScheduleBaseline.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      comparison_baseline_id: 10,
    });
  });

  it("stays idle outside the schedule route", () => {
    const { result } = renderBaselines({ enabled: false });
    expect(result.current.baselines).toEqual([]);
    expect(result.current.isLoadingList).toBe(false);
    expect(apiMocks.listScheduleBaselines).not.toHaveBeenCalled();
  });

  it("loads one list and one selected variance under Strict Mode", async () => {
    const { result } = renderBaselines({}, { wrapper: StrictMode });

    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));
    expect(apiMocks.listScheduleBaselines).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchScheduleVariance).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchScheduleVariance.mock.calls[0][1]).toMatchObject({
      baselineId: 10,
      limit: 50,
      offset: 0,
    });
    expect(result.current.selectedBaseline).toEqual(ACTIVE);
  });

  it("uses the server automatic baseline when no pointer is selected", async () => {
    apiMocks.listScheduleBaselines.mockResolvedValue({
      ...LIST,
      comparison_baseline_id: null,
    });
    const { result } = renderBaselines();

    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));
    expect(apiMocks.fetchScheduleVariance.mock.calls[0][1].baselineId).toBeNull();
    expect(result.current.comparisonBaselineId).toBeNull();
  });

  it("deduplicates capture, selects success, and ignores duplicate submit", async () => {
    const pending = deferred();
    apiMocks.createScheduleBaseline.mockReturnValue(pending.promise);
    const setScheduleSettings = vi.fn();
    const showNotice = vi.fn();
    const hook = renderBaselines({ setScheduleSettings, showNotice });
    await waitFor(() => expect(hook.result.current.variance).toEqual(VARIANCE));
    apiMocks.fetchScheduleVariance.mockClear();

    let first;
    let second;
    act(() => {
      first = hook.result.current.createBaseline({ name: "Issued Plan" });
      second = hook.result.current.createBaseline({ name: "Issued Plan" });
    });
    expect(apiMocks.createScheduleBaseline).toHaveBeenCalledTimes(1);
    expect(await second).toBeNull();

    await act(async () => {
      pending.resolve({ baseline: ACTIVE, comparison_baseline_id: 10 });
      await first;
    });
    expect(hook.result.current.comparisonBaselineId).toBe(10);
    expect(hook.result.current.viewBaselineId).toBe(10);
    expect(setScheduleSettings).toHaveBeenCalledOnce();
    expect(apiMocks.fetchScheduleVariance).toHaveBeenCalledOnce();
    expect(showNotice).toHaveBeenCalledWith(
      "success",
      "Schedule baseline captured."
    );
  });

  it("archives the viewed default atomically and requires a new selection", async () => {
    const { result } = renderBaselines();
    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));

    await act(async () => {
      await result.current.archiveBaseline(10);
    });
    expect(result.current.comparisonBaselineId).toBeNull();
    expect(result.current.viewBaselineId).toBeNull();
    expect(result.current.variance).toBeNull();
    expect(result.current.requiresSelection).toBe(true);
    expect(
      result.current.baselines.find((baseline) => baseline.id === 10).status
    ).toBe("archived");
  });

  it("views archived history without persisting it as the default", async () => {
    const { result } = renderBaselines();
    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));
    apiMocks.fetchScheduleVariance.mockClear();

    await act(async () => {
      await result.current.selectBaseline(9);
    });
    expect(apiMocks.selectScheduleBaseline).not.toHaveBeenCalled();
    expect(apiMocks.fetchScheduleVariance).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ baselineId: 9 })
    );
    expect(result.current.viewBaselineId).toBe(9);
    expect(result.current.comparisonBaselineId).toBe(10);
  });

  it("exposes local list and variance retries with global feedback", async () => {
    const reportRequestError = vi.fn();
    apiMocks.listScheduleBaselines
      .mockRejectedValueOnce(new Error("List unavailable"))
      .mockResolvedValueOnce(LIST);
    const { result } = renderBaselines({ reportRequestError });

    await waitFor(() => expect(result.current.listError).toBeTruthy());
    expect(result.current.baselines).toEqual([]);
    expect(reportRequestError).toHaveBeenCalledOnce();
    await act(async () => result.current.retryBaselines());
    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));

    apiMocks.fetchScheduleVariance.mockRejectedValueOnce(
      new Error("Variance unavailable")
    );
    await act(async () => result.current.updateFilters({ status: "slipped" }));
    expect(result.current.variance).toBeNull();
    expect(result.current.varianceError).toBeTruthy();
    apiMocks.fetchScheduleVariance.mockResolvedValueOnce(VARIANCE);
    await act(async () => result.current.retryVariance());
    expect(result.current.variance).toEqual(VARIANCE);
  });

  it("aborts old project work and rejects stale capture success and failure", async () => {
    const staleCapture = deferred();
    const showNotice = vi.fn();
    const reportRequestError = vi.fn();
    const setScheduleSettings = vi.fn();
    const hook = renderBaselines({
      showNotice,
      reportRequestError,
      setScheduleSettings,
    });
    await waitFor(() => expect(hook.result.current.variance).toEqual(VARIANCE));
    apiMocks.createScheduleBaseline.mockReturnValueOnce(staleCapture.promise);

    let capturePromise;
    act(() => {
      capturePromise = hook.result.current.createBaseline({ name: "Old" });
    });
    const captureSignal =
      apiMocks.createScheduleBaseline.mock.calls.at(-1)[2].signal;
    apiMocks.listScheduleBaselines.mockResolvedValueOnce({
      baselines: [],
      comparison_baseline_id: null,
      total: 0,
      limit: 100,
      offset: 0,
    });
    apiMocks.fetchScheduleVariance.mockResolvedValueOnce({
      baseline: null,
      summary: null,
      tasks: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    hook.rerender({ projectId: 2 });

    expect(hook.result.current.baselines).toEqual([]);
    expect(hook.result.current.variance).toBeNull();
    expect(captureSignal.aborted).toBe(true);
    await waitFor(() =>
      expect(apiMocks.listScheduleBaselines).toHaveBeenCalledWith(
        2,
        expect.any(Object)
      )
    );
    await act(async () => {
      staleCapture.resolve({ baseline: ACTIVE, comparison_baseline_id: 10 });
      await capturePromise;
    });
    expect(hook.result.current.baselines).toEqual([]);
    expect(showNotice).not.toHaveBeenCalled();
    expect(reportRequestError).not.toHaveBeenCalled();
    expect(setScheduleSettings).not.toHaveBeenCalled();
  });

  it("issues one fresh variance request per filter, search, and page change", async () => {
    const { result } = renderBaselines();
    await waitFor(() => expect(result.current.variance).toEqual(VARIANCE));
    apiMocks.fetchScheduleVariance.mockClear();

    await act(async () => result.current.updateFilters({ status: "slipped" }));
    await act(async () => result.current.updateFilters({ search: "steel" }));
    await act(async () => result.current.updateFilters({ offset: 50 }));

    expect(apiMocks.fetchScheduleVariance).toHaveBeenCalledTimes(3);
    expect(apiMocks.fetchScheduleVariance.mock.calls[2][1]).toMatchObject({
      status: "slipped",
      search: "steel",
      offset: 50,
    });
  });
});
