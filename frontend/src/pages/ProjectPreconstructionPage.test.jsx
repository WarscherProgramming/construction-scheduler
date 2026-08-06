import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectPreconstructionPage from "./ProjectPreconstructionPage";


const usePreconstructionMock = vi.hoisted(() => vi.fn());
vi.mock("../hooks/usePreconstruction", () => ({ default: usePreconstructionMock }));


const REVIEW = {
  id: 8,
  name: "Bid Review",
  description: "Electrical bid coverage",
  purpose: "bid_scope_review",
  purpose_label: "Bid Scope Review",
  status: "draft",
};
const SOURCE = {
  id: 3,
  document_id: 20,
  drawing_revision_id: null,
  display_name: "Electrical Specifications.pdf",
  document_role: "specification",
  role_label: "Specification",
  role_category: "requirement",
  extraction_status: "completed",
  current_extraction_status: "completed",
  preparation_status: "not_prepared",
  preparation_run_id: null,
  content_snapshot_id: null,
  page_count: 0,
  segment_count: 0,
  warning_count: 0,
  lineage_current: false,
  stale_reason: null,
  unavailable_reason: null,
  locked: false,
  route_target: { page: "projectDocuments", projectId: 4, documentId: 20 },
};

let state;


function makeState(overrides = {}) {
  return {
    filter: "active",
    setFilter: vi.fn(),
    reviewSets: [REVIEW],
    selectedReviewSetId: 8,
    selectReviewSet: vi.fn(),
    detail: {
      reviewSet: REVIEW,
      sources: [SOURCE],
      roles: [
        { value: "drawing", label: "Drawing", category: "requirement" },
        { value: "specification", label: "Specification", category: "requirement" },
        { value: "proposal", label: "Proposal", category: "coverage" },
      ],
      readiness: {
        ready: false,
        blockers: ["Proposal source required for bid scope review.", "AI provider is disabled."],
        warnings: ["Context document is not searchable yet."],
        requirement_source_count: 1,
        coverage_source_count: 0,
        context_source_count: 1,
        searchable_source_count: 1,
        prepared_source_count: 0,
        provider: { profile: "disabled", available: false },
      },
      runs: [],
    },
    isListLoading: false,
    isDetailLoading: false,
    isSaving: false,
    listError: null,
    detailError: null,
    candidates: [],
    isCandidateLoading: false,
    refreshList: vi.fn(),
    refreshDetail: vi.fn(),
    createReviewSet: vi.fn().mockResolvedValue(REVIEW),
    updateReviewSet: vi.fn().mockResolvedValue(REVIEW),
    archiveReviewSet: vi.fn().mockResolvedValue(REVIEW),
    addSource: vi.fn().mockResolvedValue(SOURCE),
    updateSource: vi.fn().mockResolvedValue(SOURCE),
    removeSource: vi.fn().mockResolvedValue({}),
    requestRun: vi.fn().mockResolvedValue({}),
    cancelRun: vi.fn().mockResolvedValue({}),
    retryRun: vi.fn().mockResolvedValue({}),
    prepareSource: vi.fn().mockResolvedValue({}),
    cancelPreparation: vi.fn().mockResolvedValue({}),
    retryPreparation: vi.fn().mockResolvedValue({}),
    inspectContent: vi.fn().mockResolvedValue({}),
    closeContent: vi.fn(),
    content: null,
    contentSourceId: null,
    contentQuery: { page: null, segmentOffset: 0, segmentLimit: 25, search: "" },
    isContentLoading: false,
    contentError: null,
    searchCandidates: vi.fn().mockResolvedValue([]),
    assertions: {
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
      latestAssertionSetId: null,
      taxonomyVersion: "construction-scope-1",
      sets: [],
    },
    assertionQuery: { search: "", limit: 25, offset: 0 },
    isAssertionLoading: false,
    assertionError: null,
    taxonomy: null,
    isTaxonomyLoading: false,
    loadAssertions: vi.fn().mockResolvedValue(null),
    loadTaxonomy: vi.fn().mockResolvedValue(null),
    reviewAssertion: vi.fn().mockResolvedValue({}),
    createManualAssertion: vi.fn().mockResolvedValue({}),
    ...overrides,
  };
}


function props(overrides = {}) {
  return {
    projectId: 4,
    projectName: "Riverside",
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRequestError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectPreconstructionPage", () => {
  beforeEach(() => {
    state = makeState();
    usePreconstructionMock.mockReset();
    usePreconstructionMock.mockImplementation(() => state);
  });

  it("renders one h1 with semantic review, source, readiness, and run hierarchy", () => {
    render(<ProjectPreconstructionPage {...props()} />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Preconstruction" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Review Sets" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Bid Review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Review Sources" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Readiness" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Analysis Runs" })).toBeInTheDocument();
  });

  it("shows textual readiness, provider state, role counts, and disables run", () => {
    render(<ProjectPreconstructionPage {...props()} />);
    expect(screen.getByText("AI provider is disabled")).toBeInTheDocument();
    expect(screen.getByText("Proposal source required for bid scope review.")).toBeInTheDocument();
    expect(screen.getByText("Context document is not searchable yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request Run" })).toBeDisabled();
    expect(screen.getByText("Specification · requirement")).toBeInTheDocument();
  });

  it("creates a review set in a focus-managed dialog", async () => {
    const user = userEvent.setup();
    render(<ProjectPreconstructionPage {...props()} />);
    const opener = screen.getByRole("button", { name: "Create Review Set" });
    opener.focus();
    await user.click(opener);
    const dialog = screen.getByRole("dialog", { name: "Create Review Set" });
    expect(within(dialog).getByRole("button", { name: "Close Create Review Set" })).toHaveFocus();
    await user.type(within(dialog).getByLabelText("Name"), "Scope Review");
    await user.selectOptions(within(dialog).getByLabelText("Purpose"), "subcontract_scope_review");
    await user.click(within(dialog).getByRole("button", { name: "Create Review Set" }));
    expect(state.createReviewSet).toHaveBeenCalledWith({
      name: "Scope Review",
      description: null,
      purpose: "subcontract_scope_review",
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("searches and adds a keyboard-selectable source without a binary request", async () => {
    const user = userEvent.setup();
    state.candidates = [{
      source_type: "drawing_revision",
      document_id: 44,
      drawing_revision_id: 12,
      display_name: "A6.02 - Millwork Details",
      sheet_number: "A6.02",
      revision_code: "2",
      is_current_revision: true,
      extraction_status: "completed",
    }];
    render(<ProjectPreconstructionPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Add Source" }));
    const dialog = screen.getByRole("dialog", { name: "Add Review Source" });
    await user.selectOptions(within(dialog).getByLabelText("Source type"), "drawing_revision");
    await user.type(within(dialog).getByLabelText(/Search name/), "A6.02");
    await user.click(within(dialog).getByRole("button", { name: "Search" }));
    expect(state.searchCandidates).toHaveBeenCalledWith("drawing_revision", "A6.02");
    await user.click(within(dialog).getByRole("option", { name: /A6.02/ }));
    await user.selectOptions(within(dialog).getByLabelText("Document role"), "drawing");
    await user.click(within(dialog).getByRole("button", { name: "Add Source" }));
    expect(state.addSource).toHaveBeenCalledWith({
      source_type: "drawing_revision",
      document_id: 44,
      drawing_revision_id: 12,
      document_role: "drawing",
    });
  });

  it("navigates sources and exposes safe refresh, role, remove, archive, cancel, and retry actions", async () => {
    const user = userEvent.setup();
    const pageProps = props();
    state.detail.runs = [
      { id: 10, analysis_type_label: "Provider Contract Validation", requested_at: "2026-08-05", status: "pending", attempt_count: 1, max_attempts: 3, can_cancel: true, can_retry: false },
      { id: 11, analysis_type_label: "Provider Contract Validation", requested_at: "2026-08-05", status: "failed", attempt_count: 1, max_attempts: 3, can_cancel: false, can_retry: true, failure_message: "Provider unavailable" },
    ];
    render(<ProjectPreconstructionPage {...pageProps} />);
    await user.click(screen.getByRole("button", { name: "Electrical Specifications.pdf" }));
    expect(pageProps.onNavigate).toHaveBeenCalledWith("projectDocuments", 4, SOURCE.route_target);
    await user.selectOptions(screen.getByLabelText("Role for Electrical Specifications.pdf"), "drawing");
    expect(state.updateSource).toHaveBeenCalledWith(3, { document_role: "drawing" });
    await user.click(screen.getByRole("button", { name: "Cancel Run 10" }));
    await user.click(screen.getByRole("button", { name: "Retry Run 11" }));
    expect(state.cancelRun).toHaveBeenCalledWith(10);
    expect(state.retryRun).toHaveBeenCalledWith(11);
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(state.refreshDetail).toHaveBeenCalled();
  });

  it("shows extraction and preparation separately with manual lifecycle actions", async () => {
    const user = userEvent.setup();
    const view = render(<ProjectPreconstructionPage {...props()} />);
    expect(screen.getByText("Extraction")).toBeInTheDocument();
    expect(screen.getByText("Preparation")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prepare Electrical Specifications.pdf" }));
    expect(state.prepareSource).toHaveBeenCalledWith(3);

    state = makeState({
      detail: {
        ...state.detail,
        sources: [{ ...SOURCE, preparation_status: "processing", preparation_run_id: 18 }],
      },
    });
    view.rerender(<ProjectPreconstructionPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Cancel Preparation for Electrical Specifications.pdf" }));
    expect(state.cancelPreparation).toHaveBeenCalledWith(18);

    state = makeState({
      detail: {
        ...state.detail,
        sources: [{
          ...SOURCE,
          preparation_status: "ready",
          content_snapshot_id: 9,
          page_count: 2,
          segment_count: 4,
          lineage_current: true,
        }],
      },
    });
    view.rerender(<ProjectPreconstructionPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Inspect Content for Electrical Specifications.pdf" }));
    expect(state.inspectContent).toHaveBeenCalledWith(3);
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders list/detail loading and local retry states without hiding navigation", async () => {
    const user = userEvent.setup();
    state = makeState({ isListLoading: true, reviewSets: [] });
    const view = render(<ProjectPreconstructionPage {...props()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading review sets");
    expect(screen.getByRole("button", { name: "Dashboard" })).toBeEnabled();

    state = makeState({ isListLoading: false, listError: new Error("Nope"), reviewSets: [] });
    view.rerender(<ProjectPreconstructionPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(state.refreshList).toHaveBeenCalled();
  });
});
