import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LookAheadPlanningView from "./LookAheadPlanningView";


const plan = {
  id: 4,
  project_id: 7,
  name: "Three-Week Look-Ahead",
  description: "Field coordination",
  anchor_date: "2026-08-10",
  window_days: 21,
  status: "active",
};

const item = {
  task_id: 9,
  task_available: true,
  name: "Place concrete",
  wbs: "1.2",
  order_index: 2,
  start_date: "2026-08-10",
  end_date: "2026-08-12",
  progress_status: "not_started",
  percent_complete: 0,
  is_milestone: false,
  is_critical: true,
  out_of_sequence: false,
  constraint_type: "ASAP",
  constraint_date: null,
  predecessor_count: 1,
  readiness_status: "blocked",
  blocking_reason: "Embed layout is missing",
  constraint_category: "design_information",
  constraint_owner: "Architect",
  target_resolution_date: "2026-08-11",
  commitment_note: null,
  responsible_company: { id: 3, name: "Desert Concrete", trade: "Concrete" },
  manually_included: false,
  manually_excluded: false,
  override_reason: null,
  overdue: false,
  blocked: true,
  constraint_due: true,
  commitment_missing: true,
  spans_multiple_weeks: false,
};

const detail = {
  plan,
  current_data_date: "2026-08-10",
  window_end_date: "2026-08-30",
  summary: {
    total_items: 2,
    carryover_count: 1,
    ready_count: 0,
    at_risk_count: 0,
    blocked_count: 1,
    committed_count: 0,
    overdue_count: 1,
    critical_count: 1,
    milestones_count: 0,
  },
  carryover_items: [{ ...item, task_id: 8, name: "Carryover steel", overdue: true }],
  weeks: [
    { week_index: 1, start_date: "2026-08-10", end_date: "2026-08-16", items: [item] },
    { week_index: 2, start_date: "2026-08-17", end_date: "2026-08-23", items: [] },
    { week_index: 3, start_date: "2026-08-24", end_date: "2026-08-30", items: [] },
  ],
  manual_items: [],
  excluded_items: [],
};

function lookAhead(overrides = {}) {
  return {
    plans: [plan],
    selectedPlanId: 4,
    selectedPlan: plan,
    detail,
    filters: {
      search: "",
      week: "",
      readiness: "",
      progress: "",
      companyId: "",
      criticalOnly: false,
      milestonesOnly: false,
      blockedOnly: false,
      overdueOnly: false,
      outOfSequenceOnly: false,
    },
    listError: null,
    detailError: null,
    mutationError: null,
    isLoadingList: false,
    isLoadingDetail: false,
    isCreating: false,
    isArchiving: false,
    isUpdatingItem: false,
    selectPlan: vi.fn(),
    createPlan: vi.fn().mockResolvedValue({ plan }),
    archivePlan: vi.fn().mockResolvedValue({ plan: { ...plan, status: "archived" } }),
    updateItem: vi.fn().mockResolvedValue(detail),
    updateFilters: vi.fn(),
    clearFilters: vi.fn(),
    clearMutationError: vi.fn(),
    retryPlans: vi.fn(),
    retryDetail: vi.fn(),
    ...overrides,
  };
}

const props = {
  tasks: [
    { ...item, id: 9 },
    { id: 12, name: "Future procurement", start_date: "2026-09-14", end_date: "2026-09-15" },
  ],
  companies: [{ id: 3, name: "Desert Concrete", trade: "Concrete" }],
  dataDate: "2026-08-10",
  onOpenProgress: vi.fn(),
  onOpenPlanning: vi.fn(),
};

describe("LookAheadPlanningView", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates a default three-week plan from the Data Date", async () => {
    const user = userEvent.setup();
    const state = lookAhead({ plans: [], selectedPlanId: null, selectedPlan: null, detail: null });
    render(<LookAheadPlanningView {...props} lookAhead={state} />);

    expect(screen.getByText("No look-ahead plans yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create Plan" }));
    const dialog = screen.getByRole("dialog", { name: "Create Look-Ahead Plan" });
    expect(within(dialog).getByLabelText("Planning Anchor")).toHaveValue("2026-08-10");
    expect(within(dialog).getByLabelText("Planning Window")).toHaveValue("21");
    await user.click(within(dialog).getByRole("button", { name: "Create Plan" }));
    expect(state.createPlan).toHaveBeenCalledWith({
      name: "Three-Week Look-Ahead - 2026-08-10",
      description: null,
      anchor_date: "2026-08-10",
      window_days: 21,
    });
  });

  it("renders summary, carryover, weeks, facts, and deterministic filters", async () => {
    const user = userEvent.setup();
    const state = lookAhead();
    render(<LookAheadPlanningView {...props} lookAhead={state} />);

    expect(screen.getByRole("heading", { name: "Three-Week Look-Ahead" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Carryover / Overdue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Week 1" })).toBeInTheDocument();
    expect(screen.getAllByText("Embed layout is missing")).toHaveLength(2);
    expect(screen.getAllByText("Blocker Resolution Due")).toHaveLength(2);
    await user.type(screen.getByLabelText("Search"), "concrete");
    expect(state.updateFilters).toHaveBeenCalledWith({ search: "c" });
    await user.click(screen.getByLabelText("Blocked only"));
    expect(state.updateFilters).toHaveBeenCalledWith({ blockedOnly: true });
  });

  it("edits metadata and reuses schedule progress and planning actions", async () => {
    const user = userEvent.setup();
    const state = lookAhead();
    render(<LookAheadPlanningView {...props} lookAhead={state} />);

    const taskCard = screen.getByRole("heading", { name: "Place concrete" }).closest("article");
    await user.click(within(taskCard).getByRole("button", { name: "Update Progress" }));
    await user.click(within(taskCard).getByRole("button", { name: "Edit CPM Planning" }));
    expect(props.onOpenProgress).toHaveBeenCalledWith(9);
    expect(props.onOpenPlanning).toHaveBeenCalledWith(9);

    await user.click(within(taskCard).getByRole("button", { name: "Edit Item" }));
    const dialog = screen.getByRole("dialog", { name: /Edit Look-Ahead Item/ });
    await user.selectOptions(within(dialog).getByLabelText("Readiness"), "ready");
    await user.click(within(dialog).getByRole("button", { name: "Save Item" }));
    expect(state.updateItem).toHaveBeenCalledWith(
      4,
      9,
      expect.objectContaining({ readiness_status: "ready" })
    );
  });

  it("supports manual inclusion, archive confirmation, print, and archived read-only state", async () => {
    const user = userEvent.setup();
    const print = vi.spyOn(window, "print").mockImplementation(() => {});
    const state = lookAhead();
    const { rerender } = render(<LookAheadPlanningView {...props} lookAhead={state} />);

    await user.selectOptions(screen.getByLabelText("Task to include"), "12");
    await user.click(screen.getByRole("button", { name: "Include Task" }));
    expect(screen.getByRole("dialog", { name: /Include Task/ })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Print Plan" }));
    expect(print).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Archive" }));
    await user.click(screen.getByRole("button", { name: "Archive Plan" }));
    expect(state.archivePlan).toHaveBeenCalledWith(4);

    const archived = { ...plan, status: "archived" };
    rerender(
      <LookAheadPlanningView
        {...props}
        lookAhead={lookAhead({
          plans: [archived],
          selectedPlan: archived,
          detail: { ...detail, plan: archived },
        })}
      />
    );
    expect(screen.queryByRole("button", { name: "Edit Item" })).not.toBeInTheDocument();
    print.mockRestore();
  });
});
