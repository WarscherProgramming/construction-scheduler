import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ScheduleSummaryView from "./ScheduleSummaryView";


const hook = vi.hoisted(() => ({ useScheduleHealth: vi.fn() }));
vi.mock("../../hooks/useScheduleHealth", () => ({
  default: hook.useScheduleHealth,
}));

const HEALTH = {
  category: "attention",
  summary: "Schedule needs attention for 2 current conditions.",
  reasons: [{ code: "finish_slip", label: "Forecast finish is 4 workdays late", severity: "attention", value: 4 }],
  baseline: { id: 2, name: "Contract Baseline", captured_at: "2026-07-01T12:00:00Z", project_finish: "2026-09-01" },
  data_date: "2026-08-05",
  schedule_start_date: "2026-06-01",
  executive_summary: {
    current_forecast_finish: "2026-09-07",
    project_finish_variance_workdays: 4,
    total_leaf_tasks: 12,
    not_started_tasks: 5,
    in_progress_tasks: 4,
    completed_tasks: 3,
    slipped_tasks: 2,
    newly_critical_tasks: 1,
    negative_float_tasks: 0,
    out_of_sequence_tasks: 1,
    milestones_due_next_21_days: 2,
    blocked_look_ahead_items: 1,
    committed_look_ahead_items: 3,
    labor_overallocated_days: 2,
    equipment_overallocated_days: 1,
    unassigned_executable_tasks: 2,
  },
  top_attention_items: [{
    severity: "attention",
    source: "task",
    code: "slipped_task",
    task_id: 9,
    title: "Electrical rough-in",
    wbs: "1.2",
    due_date: "2026-08-08",
    reason: "Forecast finish is later than baseline.",
  }],
};

const PROPS = {
  projectId: 7,
  onRequestError: vi.fn(),
  onDownloadCurrent: vi.fn(),
  onDownloadExecutive: vi.fn(),
  isDownloadingCurrent: false,
  isDownloadingExecutive: false,
};

describe("ScheduleSummaryView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hook.useScheduleHealth.mockReturnValue({
      health: HEALTH,
      error: null,
      isLoading: false,
      retry: vi.fn(),
    });
  });

  it("renders explainable health, executive metrics, and bounded attention", () => {
    render(<ScheduleSummaryView {...PROPS} />);

    expect(screen.getByRole("heading", { name: HEALTH.summary })).toBeInTheDocument();
    expect(screen.getByText(/Contract Baseline/)).toBeInTheDocument();
    expect(screen.getByText("4 workdays")).toBeInTheDocument();
    expect(screen.getByText(/Forecast finish is 4 workdays late/)).toBeInTheDocument();
    expect(screen.getByText("Electrical rough-in")).toBeInTheDocument();
  });

  it("keeps both report downloads explicit and keyboard operable", async () => {
    const user = userEvent.setup();
    render(<ScheduleSummaryView {...PROPS} />);

    const executive = screen.getByRole("button", { name: "Download Executive Schedule Report" });
    executive.focus();
    expect(executive).toHaveFocus();
    await user.click(executive);
    await user.click(screen.getByRole("button", { name: "Download Current Schedule PDF" }));

    expect(PROPS.onDownloadExecutive).toHaveBeenCalledOnce();
    expect(PROPS.onDownloadCurrent).toHaveBeenCalledOnce();
  });

  it("isolates failure with a focused retry", async () => {
    const retry = vi.fn();
    hook.useScheduleHealth.mockReturnValue({
      health: null,
      error: new Error("offline"),
      isLoading: false,
      retry,
    });
    render(<ScheduleSummaryView {...PROPS} />);

    expect(screen.getByText("Schedule summary unavailable")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry Schedule Summary" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("uses stable skeleton regions while loading", () => {
    hook.useScheduleHealth.mockReturnValue({
      health: null,
      error: null,
      isLoading: true,
      retry: vi.fn(),
    });
    render(<ScheduleSummaryView {...PROPS} />);

    expect(screen.getByLabelText("Loading schedule summary")).toBeInTheDocument();
  });
});
