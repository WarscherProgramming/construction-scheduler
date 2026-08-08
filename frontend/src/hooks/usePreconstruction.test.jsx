import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import usePreconstruction from "./usePreconstruction";


const apiMocks = vi.hoisted(() => ({
  addPreconstructionReviewSource: vi.fn(),
  archivePreconstructionReviewSet: vi.fn(),
  cancelPreconstructionPreparationRun: vi.fn(),
  cancelPreconstructionRun: vi.fn(),
  archivePreconstructionComparisonPlan: vi.fn(),
  createPreconstructionComparisonPlan: vi.fn(),
  createPreconstructionManualFinding: vi.fn(),
  getPreconstructionComparisonReadiness: vi.fn(),
  listPreconstructionComparisonPlans: vi.fn(),
  listPreconstructionFindingSets: vi.fn(),
  listPreconstructionFindings: vi.fn(),
  reviewPreconstructionFinding: vi.fn(),
  runPreconstructionComparison: vi.fn(),
  updatePreconstructionComparisonPlan: vi.fn(),
  createPreconstructionManualAssertion: vi.fn(),
  createPreconstructionReviewSet: vi.fn(),
  createPreconstructionRun: vi.fn(),
  getPreconstructionReadiness: vi.fn(),
  getPreconstructionScopeTaxonomy: vi.fn(),
  getPreconstructionSourceContent: vi.fn(),
  getPreconstructionReviewSet: vi.fn(),
  listPreconstructionAssertionSets: vi.fn(),
  listPreconstructionAssertions: vi.fn(),
  listPreconstructionReviewSets: vi.fn(),
  listPreconstructionReviewSources: vi.fn(),
  listPreconstructionRuns: vi.fn(),
  listPreconstructionSourceCandidates: vi.fn(),
  removePreconstructionReviewSource: vi.fn(),
  preparePreconstructionSource: vi.fn(),
  reviewPreconstructionAssertion: vi.fn(),
  retryPreconstructionPreparationRun: vi.fn(),
  retryPreconstructionRun: vi.fn(),
  updatePreconstructionReviewSet: vi.fn(),
  updatePreconstructionReviewSource: vi.fn(),
  listPreconstructionExecutionMetrics: vi.fn(),
  listPreconstructionFindingFollowUps: vi.fn(),
  createPreconstructionFollowUp: vi.fn(),
  updatePreconstructionFollowUp: vi.fn(),
  linkPreconstructionFollowUp: vi.fn(),
  closePreconstructionFollowUp: vi.fn(),
}));

const EMPTY_ASSERTION_PAGE = {
  items: [],
  total: 0,
  limit: 25,
  offset: 0,
  summary: {
    total: 0,
    proposed: 0,
    accepted: 0,
    rejected: 0,
    needs_review: 0,
    superseded: 0,
    manual: 0,
  },
  latest_assertion_set_id: null,
  taxonomy_version: "construction-scope-1",
};
vi.mock("../services/api", () => apiMocks);


const REVIEW = {
  id: 8,
  project_id: 1,
  name: "Bid Review",
  description: null,
  purpose: "bid_scope_review",
  purpose_label: "Bid Scope Review",
  status: "draft",
};
const READINESS = {
  ready: false,
  blockers: ["AI provider is disabled."],
  warnings: [],
  provider: { profile: "disabled", available: false },
};


function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
}


describe("usePreconstruction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listPreconstructionComparisonPlans.mockResolvedValue({
      items: [], total: 0, comparison_types: [],
    });
    apiMocks.listPreconstructionAssertions.mockResolvedValue(EMPTY_ASSERTION_PAGE);
    apiMocks.listPreconstructionAssertionSets.mockResolvedValue({ items: [], total: 0 });
    apiMocks.listPreconstructionReviewSets.mockResolvedValue({ items: [REVIEW], total: 1 });
    apiMocks.getPreconstructionReviewSet.mockResolvedValue(REVIEW);
    apiMocks.listPreconstructionReviewSources.mockResolvedValue({ items: [], roles: [] });
    apiMocks.getPreconstructionReadiness.mockResolvedValue(READINESS);
    apiMocks.listPreconstructionRuns.mockResolvedValue({ items: [], total: 0 });
    apiMocks.createPreconstructionReviewSet.mockResolvedValue(REVIEW);
    apiMocks.updatePreconstructionReviewSet.mockResolvedValue({ ...REVIEW, description: "Updated" });
    apiMocks.archivePreconstructionReviewSet.mockResolvedValue({ ...REVIEW, status: "archived" });
    apiMocks.addPreconstructionReviewSource.mockResolvedValue({ id: 2 });
    apiMocks.updatePreconstructionReviewSource.mockResolvedValue({ id: 2 });
    apiMocks.removePreconstructionReviewSource.mockResolvedValue({ message: "removed" });
    apiMocks.preparePreconstructionSource.mockResolvedValue({ run_id: 6, status: "pending" });
    apiMocks.cancelPreconstructionPreparationRun.mockResolvedValue({ run_id: 6, status: "cancelled" });
    apiMocks.retryPreconstructionPreparationRun.mockResolvedValue({ run_id: 6, status: "pending" });
    apiMocks.getPreconstructionSourceContent.mockResolvedValue({
      source: { id: 2 },
      snapshot: { id: 9 },
      pages: [],
      segments: [],
      pagination: { offset: 0, limit: 25, total: 0 },
    });
    apiMocks.createPreconstructionRun.mockResolvedValue({ id: 4, status: "pending" });
    apiMocks.cancelPreconstructionRun.mockResolvedValue({ id: 4, status: "cancelled" });
    apiMocks.retryPreconstructionRun.mockResolvedValue({ id: 4, status: "pending" });
    apiMocks.listPreconstructionSourceCandidates.mockResolvedValue({ items: [{ document_id: 3 }] });
    apiMocks.listPreconstructionFindingFollowUps.mockResolvedValue({
      items: [],
      total: 0,
      actions: [{ value: "rfi", label: "Request for Information", target_type: "rfi" }],
      available_actions: [
        { value: "rfi", label: "Request for Information", target_type: "rfi" },
      ],
      drafts: [{ action_type: "rfi", draft_title: "Draft", draft_body: "Body" }],
      finding_status: "accepted",
      eligible: true,
    });
    apiMocks.createPreconstructionFollowUp.mockResolvedValue({ follow_up: { id: 12 } });
    apiMocks.linkPreconstructionFollowUp.mockResolvedValue({ follow_up: { id: 12 } });
    apiMocks.closePreconstructionFollowUp.mockResolvedValue({ follow_up: { id: 12 } });
    apiMocks.reviewPreconstructionFinding.mockResolvedValue({ finding: { id: 91 } });
    apiMocks.listPreconstructionExecutionMetrics.mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      summary: {
        total_executions: 0,
        total_duration_ms: 0,
        estimated_cost_micros: null,
        estimated_cost_display: null,
        cost_rate_configured: false,
        by_kind: [],
      },
      metrics_enabled: true,
      metrics_version: "preconstruction-execution-1",
    });
    apiMocks.runPreconstructionComparison.mockResolvedValue({ id: 3 });
  });

  it("passes the manifest-reuse choice explicitly and defaults it off", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));

    await act(async () => { await result.current.runComparison(5); });
    expect(apiMocks.runPreconstructionComparison).toHaveBeenCalledWith(1, 5, {
      reuse_identical_manifest: false,
    });

    await act(async () => {
      await result.current.runComparison(5, { reuseIdenticalManifest: true });
    });
    expect(apiMocks.runPreconstructionComparison).toHaveBeenLastCalledWith(1, 5, {
      reuse_identical_manifest: true,
    });
  });

  it("loads follow-ups for one finding at a time and clears them on close", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));

    expect(result.current.followUps.items).toEqual([]);
    expect(apiMocks.listPreconstructionFindingFollowUps).not.toHaveBeenCalled();

    await act(async () => { await result.current.loadFollowUps(91); });
    expect(apiMocks.listPreconstructionFindingFollowUps).toHaveBeenCalledWith(
      1,
      91,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(result.current.followUps.findingId).toBe(91);
    expect(result.current.followUps.eligible).toBe(true);

    act(() => result.current.closeFollowUps());
    expect(result.current.followUps.findingId).toBeNull();
    expect(result.current.followUps.availableActions).toEqual([]);
  });

  it("refreshes an open follow-up panel after the finding review changes", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));
    act(() => result.current.selectReviewSet(8));
    await waitFor(() => expect(result.current.detail.reviewSet).toEqual(REVIEW));

    await act(async () => { await result.current.loadFollowUps(91); });
    apiMocks.listPreconstructionFindingFollowUps.mockClear();

    await act(async () => {
      await result.current.reviewFinding(91, { decision: "needs_review" });
    });
    expect(apiMocks.listPreconstructionFindingFollowUps).toHaveBeenCalledWith(
      1,
      91,
      expect.anything()
    );

    // A review on a different finding leaves the open panel alone.
    apiMocks.listPreconstructionFindingFollowUps.mockClear();
    await act(async () => {
      await result.current.reviewFinding(92, { decision: "accepted" });
    });
    expect(apiMocks.listPreconstructionFindingFollowUps).not.toHaveBeenCalled();
  });

  it("raises, links, and closes follow-ups without touching workflow endpoints", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));

    await act(async () => {
      await result.current.createFollowUp(91, { action_type: "rfi" });
    });
    expect(apiMocks.createPreconstructionFollowUp).toHaveBeenCalledWith(1, 91, {
      action_type: "rfi",
    });

    await act(async () => {
      await result.current.linkFollowUp(91, 12, { target_type: "rfi", target_id: 7 });
    });
    expect(apiMocks.linkPreconstructionFollowUp).toHaveBeenCalledWith(1, 12, {
      target_type: "rfi",
      target_id: 7,
    });

    await act(async () => {
      await result.current.closeFollowUp(91, 12, { status: "completed" });
    });
    expect(apiMocks.closePreconstructionFollowUp).toHaveBeenCalledWith(1, 12, {
      status: "completed",
    });

    // Each mutation refreshes only the affected finding's panel.
    expect(apiMocks.listPreconstructionFindingFollowUps).toHaveBeenCalledTimes(3);
  });

  it("loads one bounded list in Strict Mode and loads selected details", async () => {
    const { result } = renderHook(
      () => usePreconstruction({ projectId: 1 }),
      { wrapper: StrictMode }
    );
    await waitFor(() => expect(result.current.isListLoading).toBe(false));
    expect(apiMocks.listPreconstructionReviewSets).toHaveBeenCalledTimes(1);
    expect(apiMocks.listPreconstructionReviewSets).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ state: "active", limit: 100, signal: expect.any(AbortSignal) })
    );

    act(() => result.current.selectReviewSet(8));
    await waitFor(() => expect(result.current.detail.reviewSet).toEqual(REVIEW));
    expect(apiMocks.getPreconstructionReviewSet).toHaveBeenCalledTimes(1);
    expect(apiMocks.listPreconstructionReviewSources).toHaveBeenCalledTimes(1);
    expect(apiMocks.getPreconstructionReadiness).toHaveBeenCalledTimes(1);
    expect(apiMocks.listPreconstructionRuns).toHaveBeenCalledTimes(1);
  });

  it("supports review, source, run, and candidate mutations", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));
    act(() => result.current.selectReviewSet(8));
    await waitFor(() => expect(result.current.detail.reviewSet).toEqual(REVIEW));

    await act(async () => {
      await result.current.updateReviewSet({ description: "Updated" });
      await result.current.addSource({ document_id: 3 });
      await result.current.updateSource(2, { document_role: "drawing" });
      await result.current.removeSource(2);
      await result.current.prepareSource(2);
      await result.current.cancelPreparation(6);
      await result.current.retryPreparation(6);
      await result.current.requestRun();
      await result.current.cancelRun(4);
      await result.current.retryRun(4);
      await result.current.searchCandidates("document", "plans");
    });

    expect(apiMocks.updatePreconstructionReviewSet).toHaveBeenCalledWith(1, 8, { description: "Updated" });
    expect(apiMocks.addPreconstructionReviewSource).toHaveBeenCalledWith(1, 8, { document_id: 3 });
    expect(apiMocks.createPreconstructionRun).toHaveBeenCalledWith(1, 8, { analysis_type: "content_contract_validation" });
    expect(apiMocks.preparePreconstructionSource).toHaveBeenCalledWith(1, 8, 2);
    expect(apiMocks.cancelPreconstructionPreparationRun).toHaveBeenCalledWith(1, 6);
    expect(apiMocks.retryPreconstructionPreparationRun).toHaveBeenCalledWith(1, 6);
    expect(apiMocks.listPreconstructionSourceCandidates).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ sourceType: "document", search: "plans", limit: 20, signal: expect.any(AbortSignal) })
    );
    expect(result.current.candidates).toEqual([{ document_id: 3 }]);
  });

  it("loads one selected source content request and clears it on review switch", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));
    act(() => result.current.selectReviewSet(8));
    await waitFor(() => expect(result.current.detail.reviewSet).toEqual(REVIEW));

    await act(async () => {
      await result.current.inspectContent(2, {
        page: 3,
        segmentOffset: 25,
        segmentLimit: 25,
        search: "lighting",
      });
    });
    expect(apiMocks.getPreconstructionSourceContent).toHaveBeenCalledWith(
      1,
      8,
      2,
      expect.objectContaining({
        page: 3,
        segmentOffset: 25,
        segmentLimit: 25,
        search: "lighting",
        signal: expect.any(AbortSignal),
      })
    );
    expect(result.current.content.snapshot.id).toBe(9);
    act(() => result.current.selectReviewSet(9));
    expect(result.current.content).toBeNull();
    expect(result.current.contentSourceId).toBeNull();
  });

  it("rejects stale content after a project switch", async () => {
    const pending = deferred();
    apiMocks.getPreconstructionSourceContent.mockReturnValue(pending.promise);
    const hook = renderHook(
      ({ projectId }) => usePreconstruction({ projectId }),
      { initialProps: { projectId: 1 } }
    );
    await waitFor(() => expect(hook.result.current.isListLoading).toBe(false));
    act(() => hook.result.current.selectReviewSet(8));
    await waitFor(() => expect(hook.result.current.detail.reviewSet).toEqual(REVIEW));
    let request;
    act(() => { request = hook.result.current.inspectContent(2); });
    await waitFor(() => expect(apiMocks.getPreconstructionSourceContent).toHaveBeenCalled());
    const signal = apiMocks.getPreconstructionSourceContent.mock.calls[0][3].signal;
    hook.rerender({ projectId: 2 });
    expect(signal.aborted).toBe(true);
    await act(async () => {
      pending.resolve({ snapshot: { id: 9 } });
      await request;
    });
    expect(hook.result.current.content).toBeNull();
  });

  it("creates, selects, archives, and filters review sets", async () => {
    const { result } = renderHook(() => usePreconstruction({ projectId: 1 }));
    await waitFor(() => expect(result.current.isListLoading).toBe(false));
    await act(async () => {
      await result.current.createReviewSet({ name: "Bid", purpose: "bid_scope_review" });
    });
    expect(result.current.selectedReviewSetId).toBe(8);
    await act(async () => {
      await result.current.archiveReviewSet();
    });
    expect(result.current.selectedReviewSetId).toBeNull();
    act(() => result.current.setFilter("archived"));
    await waitFor(() => expect(apiMocks.listPreconstructionReviewSets).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({ state: "archived" })
    ));
  });

  it("clears immediately and rejects stale detail after a project switch", async () => {
    const pending = deferred();
    apiMocks.getPreconstructionReviewSet.mockReturnValue(pending.promise);
    const hook = renderHook(
      ({ projectId }) => usePreconstruction({ projectId }),
      { initialProps: { projectId: 1 } }
    );
    await waitFor(() => expect(hook.result.current.isListLoading).toBe(false));
    act(() => hook.result.current.selectReviewSet(8));
    await waitFor(() => expect(apiMocks.getPreconstructionReviewSet).toHaveBeenCalled());
    const signal = apiMocks.getPreconstructionReviewSet.mock.calls[0][2].signal;

    hook.rerender({ projectId: 2 });
    expect(signal.aborted).toBe(true);
    await act(async () => {
      pending.resolve(REVIEW);
      await pending.promise;
    });
    await waitFor(() => expect(hook.result.current.selectedReviewSetId).toBeNull());
    expect(hook.result.current.detail.reviewSet).toBeNull();
  });

  it("reports list and detail failures and retries locally", async () => {
    const error = new Error("Unavailable");
    const onError = vi.fn();
    apiMocks.listPreconstructionReviewSets.mockRejectedValueOnce(error).mockResolvedValueOnce({ items: [REVIEW] });
    const { result } = renderHook(() => usePreconstruction({ projectId: 1, onError }));
    await waitFor(() => expect(result.current.listError).toBe(error));
    expect(onError).toHaveBeenCalledWith("Unable to load preconstruction review sets", error);
    await act(async () => { await result.current.refreshList(); });
    expect(result.current.reviewSets).toEqual([REVIEW]);
  });
});
