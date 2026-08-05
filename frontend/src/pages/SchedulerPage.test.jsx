import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SchedulerPage from "./SchedulerPage";


vi.mock("../components/schedule/ScheduleSummaryView", () => ({
  default: ({ onDownloadExecutive }) => (
    <section aria-label="Schedule Summary Content">
      <h2>Schedule health summary</h2>
      <button type="button" onClick={onDownloadExecutive}>Download Executive Schedule Report</button>
    </section>
  ),
}));


const baseBaselines = {
  baselines: [],
  selectedBaseline: null,
  viewBaselineId: null,
  variance: null,
  filters: {
    includeSummaries: true,
    status: "",
    criticalChange: "",
    search: "",
    sort: "wbs",
    order: "asc",
    limit: 50,
    offset: 0,
  },
  listError: null,
  varianceError: null,
  mutationError: null,
  isLoadingList: false,
  isLoadingVariance: false,
  isCreating: false,
  isArchiving: false,
  isSelecting: false,
  requiresSelection: false,
  retryBaselines: vi.fn(),
  retryVariance: vi.fn(),
  createBaseline: vi.fn(),
  archiveBaseline: vi.fn(),
  selectBaseline: vi.fn(),
  updateFilters: vi.fn(),
  clearMutationError: vi.fn(),
};

const baseLookAhead = {
  plans: [],
  selectedPlanId: null,
  selectedPlan: null,
  detail: null,
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
  retryPlans: vi.fn(),
  retryDetail: vi.fn(),
  selectPlan: vi.fn(),
  createPlan: vi.fn(),
  archivePlan: vi.fn(),
  updateItem: vi.fn(),
  updateFilters: vi.fn(),
  clearFilters: vi.fn(),
  clearMutationError: vi.fn(),
};

const baseProjectResources = {
  crews: [],
  equipment: [],
  assignments: [],
  availability: [],
  isLoading: false,
  isLoadingAssignments: false,
  isLoadingAvailability: false,
  isPending: vi.fn(() => false),
  loadAssignments: vi.fn().mockResolvedValue({ assignments: [] }),
  loadAvailability: vi.fn(),
  createAssignment: vi.fn(),
  updateAssignment: vi.fn(),
  deleteAssignment: vi.fn(),
};

const baseResourceLoading = {
  data: null,
  error: null,
  isLoading: true,
  load: vi.fn(),
  retry: vi.fn(),
};


const baseProps = {
  tasks: [],
  templates: [],
  scheduleSettings: {
    project_id: 1,
    schedule_start_date: "2026-06-22",
    data_date: "2026-06-22",
  },
  selectedProjectId: 1,
  selectedTaskId: null,
  editingCell: null,
  editValue: "",
  templateName: "",
  selectedTemplateId: "",
  scheduleView: "table",
  baselines: baseBaselines,
  lookAhead: baseLookAhead,
  projectResources: baseProjectResources,
  resourceLoading: baseResourceLoading,
  setSelectedTaskId: vi.fn(),
  setEditValue: vi.fn(),
  setTemplateName: vi.fn(),
  setSelectedTemplateId: vi.fn(),
  setScheduleView: vi.fn(),
  onNavigate: vi.fn(),
  onSaveTemplate: vi.fn(),
  onApplyTemplate: vi.fn(),
  onExport: vi.fn(),
  onExportExecutive: vi.fn(),
  onRequestError: vi.fn(),
  onLogout: vi.fn(),
  onDragEnd: vi.fn(),
  onCellClick: vi.fn(),
  onCellSave: vi.fn(),
  onCellCancel: vi.fn(),
  onDelete: vi.fn(),
  onIndent: vi.fn(),
  onOutdent: vi.fn(),
  onToggleCollapse: vi.fn(),
  onRetryTasks: vi.fn(),
  onUpdateScheduleStart: vi.fn(),
  onUpdateDataDate: vi.fn(),
  onOpenTaskProgress: vi.fn(),
  onCloseTaskProgress: vi.fn(),
  onUpdateTaskProgress: vi.fn(),
  onOpenTaskPlanning: vi.fn(),
  onCloseTaskPlanning: vi.fn(),
  onUpdateTaskPlanning: vi.fn(),
  getEmptyRow: () => ({ id: null, name: "" }),
  formatDate: (value) => value,
  taskHasChildren: () => false,
  isTaskHiddenByCollapsedParent: () => false,
  getTaskDepth: () => 0,
};


describe("SchedulerPage", () => {
  it("opens schedule summary as the fifth mode and exposes executive reporting", async () => {
    const user = userEvent.setup();
    const onExportExecutive = vi.fn();
    render(
      <SchedulerPage
        {...baseProps}
        onExportExecutive={onExportExecutive}
      />
    );

    await user.click(screen.getByRole("button", { name: "Schedule Summary" }));
    expect(screen.getByRole("region", { name: "Schedule Summary" })).toBeInTheDocument();
    expect(screen.getByText("Schedule health summary")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Download Executive Schedule Report" }));
    expect(onExportExecutive).toHaveBeenCalledOnce();
  });

  it("opens resource loading as the fourth schedule mode", async () => {
    const user = userEvent.setup();
    render(<SchedulerPage {...baseProps} />);

    await user.click(screen.getByRole("button", { name: "Resource Loading" }));
    expect(screen.getByRole("region", { name: "Resource Loading" })).toBeInTheDocument();
    expect(screen.getByText("Live Resource Loading")).toBeInTheDocument();
    expect(baseResourceLoading.load).toHaveBeenCalledOnce();
  });

  it("opens resource assignment only for an executable schedule row", async () => {
    const user = userEvent.setup();
    const task = { id: 9, name: "Rough-in", duration: 2, dependencies: [] };
    render(<SchedulerPage {...baseProps} tasks={[task]} />);

    await user.click(screen.getByRole("button", { name: "Assign resources to Rough-in" }));
    expect(screen.getByRole("dialog", { name: "Task Resources" })).toBeInTheDocument();
    expect(baseProjectResources.loadAssignments).toHaveBeenCalledWith(9);
  });

  it("opens look-ahead planning inside the existing scheduler route", async () => {
    const user = userEvent.setup();
    render(<SchedulerPage {...baseProps} />);

    await user.click(
      screen.getByRole("button", { name: "Look-Ahead Planning" })
    );
    expect(
      screen.getByRole("region", { name: "Look-Ahead Planning" })
    ).toBeInTheDocument();
    expect(screen.getByText("No look-ahead plans yet")).toBeInTheDocument();
    expect(baseLookAhead.retryDetail).toHaveBeenCalledOnce();
  });

  it("shows dependency guidance and an actionable empty state", () => {
    render(<SchedulerPage {...baseProps} />);

    expect(screen.getByText("Dependency format help")).toBeInTheDocument();
    expect(
      screen.getByText(/No tasks yet\. Use Add task below/)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Add task" })).toBeInTheDocument();
  });

  it("marks schedule identity columns for sticky positioning", () => {
    render(<SchedulerPage {...baseProps} />);

    expect(screen.getByRole("columnheader", { name: "ID" })).toHaveClass(
      "schedule-sticky-0"
    );
    expect(screen.getByRole("columnheader", { name: "Task" })).toHaveClass(
      "schedule-sticky-1"
    );
  });

  it("numbers tasks from one within the current schedule", () => {
    render(
      <SchedulerPage
        {...baseProps}
        tasks={[
          {
            id: 212,
            name: "Mobilization",
            duration: 1,
            predecessor: null,
          },
        ]}
      />
    );

    expect(
      screen.getByRole("button", {
        name: "Reorder schedule task 1: Mobilization",
      })
    ).toBeInTheDocument();
  });

  it("moves the roving cell cursor with arrow keys", async () => {
    const user = userEvent.setup();
    const tasks = [
      { id: 1, name: "Mobilization", duration: 1, predecessor: null },
      { id: 2, name: "Grading", duration: 2, predecessor: null },
    ];

    render(<SchedulerPage {...baseProps} tasks={tasks} />);

    const firstName = screen.getByRole("button", { name: "Edit task 1 name" });

    // Roving tabindex: only the cursor cell is in the tab order.
    expect(firstName).toHaveAttribute("tabindex", "0");
    expect(
      screen.getByRole("button", { name: "Edit task 1 duration" })
    ).toHaveAttribute("tabindex", "-1");

    firstName.focus();

    await user.keyboard("{ArrowRight}");
    expect(
      screen.getByRole("button", { name: "Edit task 1 duration" })
    ).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(
      screen.getByRole("button", { name: "Edit task 2 duration" })
    ).toHaveFocus();

    await user.keyboard("{ArrowLeft}");
    expect(
      screen.getByRole("button", { name: "Edit task 2 name" })
    ).toHaveFocus();

    await user.keyboard("{ArrowUp}");
    expect(firstName).toHaveFocus();
  });

  it("wraps Tab across rows and opens the focused cell with Enter", async () => {
    const user = userEvent.setup();
    const onCellClick = vi.fn();
    const tasks = [
      { id: 1, name: "Mobilization", duration: 1, predecessor: null },
      { id: 2, name: "Grading", duration: 2, predecessor: null },
    ];

    render(
      <SchedulerPage {...baseProps} tasks={tasks} onCellClick={onCellClick} />
    );

    const firstPredecessor = screen.getByRole("button", {
      name: "Edit task 1 predecessor",
    });
    firstPredecessor.focus();

    await user.keyboard("{Tab}");
    expect(
      screen.getByRole("button", { name: "Edit task 2 name" })
    ).toHaveFocus();

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(firstPredecessor).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(onCellClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1 }),
      "predecessor"
    );
  });

  it("applies hierarchy controls to the selected task", async () => {
    const user = userEvent.setup();
    const task = {
      id: 212,
      name: "Mobilization",
      duration: 1,
      predecessor: null,
      parent_task_id: 100,
    };
    const onIndent = vi.fn();
    const onOutdent = vi.fn();

    render(
      <SchedulerPage
        {...baseProps}
        tasks={[
          { id: 100, name: "Site Work", parent_task_id: null },
          task,
        ]}
        selectedTaskId={task.id}
        onIndent={onIndent}
        onOutdent={onOutdent}
      />
    );

    expect(screen.getByText("Task 1.1 selected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Indent" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Outdent" }));
    expect(onOutdent).toHaveBeenCalledWith(task);
  });

  it("renders project progress metrics and a leaf-task progress dialog", () => {
    const progressTask = {
      id: 212,
      name: "Mobilization",
      duration: 2,
      predecessor: null,
      parent_task_id: null,
      progress_status: "in_progress",
      percent_complete: 50,
      remaining_duration: 1,
      actual_start_date: "2026-06-20",
      actual_finish_date: null,
    };

    render(
      <SchedulerPage
        {...baseProps}
        tasks={[progressTask]}
        progressTaskId={progressTask.id}
        scheduleSummary={{
          total_leaf_tasks: 1,
          not_started_count: 0,
          in_progress_count: 1,
          completed_count: 0,
          out_of_sequence_count: 0,
          percent_complete_weighted: 50,
          data_date: "2026-06-22",
          forecast_project_finish: "2026-06-23",
        }}
      />
    );

    expect(screen.getByText("50%", { selector: "dd" })).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Update Progress: Mobilization" })
    ).toBeInTheDocument();
  });

  it("opens planning for a leaf and displays all predecessors", async () => {
    const user = userEvent.setup();
    const onOpenTaskPlanning = vi.fn();
    const tasks = [
      { id: 1, name: "First", duration: 2, dependencies: [] },
      { id: 2, name: "Second", duration: 2, dependencies: [] },
      {
        id: 3,
        name: "Release",
        duration: 1,
        is_milestone: false,
        constraint_type: "SNET",
        constraint_date: "2026-06-23",
        dependencies: [
          {
            predecessor_task_id: 1,
            dependency_type: "FF",
            lag_days: -2,
          },
          {
            predecessor_task_id: 2,
            dependency_type: "SF",
            lag_days: 3,
          },
        ],
      },
    ];

    render(
      <SchedulerPage
        {...baseProps}
        tasks={tasks}
        planningTaskId={3}
        onOpenTaskPlanning={onOpenTaskPlanning}
      />
    );

    expect(screen.getByText("1FF-2, 2SF+3")).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Plan Task: Release" })
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Edit planning for First" })
    );
    expect(onOpenTaskPlanning).toHaveBeenCalledWith(tasks[0]);
  });

  it("keeps summary progress derived and rejects direct dialog mounting", () => {
    const parent = {
      id: 1,
      name: "Site Work",
      duration: 1,
      parent_task_id: null,
      progress_status: "in_progress",
      percent_complete: 50,
      remaining_duration: null,
    };
    const child = {
      id: 2,
      name: "Grading",
      duration: 2,
      parent_task_id: 1,
      progress_status: "in_progress",
      percent_complete: 50,
      remaining_duration: 1,
    };

    render(
      <SchedulerPage
        {...baseProps}
        tasks={[parent, child]}
        progressTaskId={parent.id}
        taskHasChildren={(id) => id === parent.id}
      />
    );

    expect(screen.getByText("Derived")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows only the progress loading state while tasks load", () => {
    render(
      <SchedulerPage
        {...baseProps}
        isLoadingTasks
        scheduleSummary={{ percent_complete_weighted: 99 }}
      />
    );

    expect(screen.getByText("Loading schedule progress...")).toBeInTheDocument();
    expect(screen.queryByText("99%", { selector: "dd" }))
      .not.toBeInTheDocument();
    expect(screen.getByText("Loading project schedule…")).toBeInTheDocument();
  });

  it("switches between the current schedule and baseline comparison", async () => {
    const user = userEvent.setup();
    const retryVariance = vi.fn();

    render(
      <SchedulerPage
        {...baseProps}
        baselines={{ ...baseBaselines, retryVariance }}
      />
    );

    await user.click(
      screen.getByRole("button", { name: "Baseline Comparison" })
    );

    expect(retryVariance).toHaveBeenCalledOnce();
    expect(
      screen.getByText(/No comparison baseline is available/)
    ).toBeInTheDocument();
    expect(screen.queryByText("Dependency format help")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Current Schedule" })
    );
    expect(screen.getByText("Dependency format help")).toBeInTheDocument();
  });
});
