import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import usePreconstruction from "./usePreconstruction";


const apiMocks = vi.hoisted(() => ({
  addPreconstructionReviewSource: vi.fn(),
  archivePreconstructionReviewSet: vi.fn(),
  cancelPreconstructionRun: vi.fn(),
  createPreconstructionReviewSet: vi.fn(),
  createPreconstructionRun: vi.fn(),
  getPreconstructionReadiness: vi.fn(),
  getPreconstructionReviewSet: vi.fn(),
  listPreconstructionReviewSets: vi.fn(),
  listPreconstructionReviewSources: vi.fn(),
  listPreconstructionRuns: vi.fn(),
  listPreconstructionSourceCandidates: vi.fn(),
  removePreconstructionReviewSource: vi.fn(),
  retryPreconstructionRun: vi.fn(),
  updatePreconstructionReviewSet: vi.fn(),
  updatePreconstructionReviewSource: vi.fn(),
}));
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
    apiMocks.createPreconstructionRun.mockResolvedValue({ id: 4, status: "pending" });
    apiMocks.cancelPreconstructionRun.mockResolvedValue({ id: 4, status: "cancelled" });
    apiMocks.retryPreconstructionRun.mockResolvedValue({ id: 4, status: "pending" });
    apiMocks.listPreconstructionSourceCandidates.mockResolvedValue({ items: [{ document_id: 3 }] });
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
      await result.current.requestRun();
      await result.current.cancelRun(4);
      await result.current.retryRun(4);
      await result.current.searchCandidates("document", "plans");
    });

    expect(apiMocks.updatePreconstructionReviewSet).toHaveBeenCalledWith(1, 8, { description: "Updated" });
    expect(apiMocks.addPreconstructionReviewSource).toHaveBeenCalledWith(1, 8, { document_id: 3 });
    expect(apiMocks.createPreconstructionRun).toHaveBeenCalledWith(1, 8, { analysis_type: "provider_contract_validation" });
    expect(apiMocks.listPreconstructionSourceCandidates).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ sourceType: "document", search: "plans", limit: 20, signal: expect.any(AbortSignal) })
    );
    expect(result.current.candidates).toEqual([{ document_id: 3 }]);
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
