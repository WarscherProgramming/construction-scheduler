import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TaskPlanningDialog from "./TaskPlanningDialog";


const tasks = [
  {
    id: 1,
    name: "Excavation",
    duration: 3,
    progress_status: "not_started",
    is_milestone: false,
    constraint_type: "ASAP",
    constraint_date: null,
    dependencies: [],
  },
  { id: 2, name: "Footings", duration: 2 },
  { id: 3, name: "Steel", duration: 4 },
];

function renderDialog(overrides = {}) {
  const props = {
    task: tasks[0],
    tasks,
    displayId: "1",
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
  render(<TaskPlanningDialog {...props} />);
  return props;
}

describe("TaskPlanningDialog", () => {
  it("submits milestones, dated constraints, and multiple dependencies", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    await user.click(screen.getByRole("checkbox", { name: "Milestone" }));
    await user.selectOptions(
      screen.getByLabelText("Constraint"),
      "SNET"
    );
    await user.type(screen.getByLabelText("Constraint Date"), "2026-03-09");
    await user.click(screen.getByRole("button", { name: "Add Predecessor" }));
    await user.selectOptions(screen.getByLabelText("Type"), "FF");
    await user.clear(screen.getByLabelText("Lag"));
    await user.type(screen.getByLabelText("Lag"), "-2");
    await user.click(screen.getByRole("button", { name: "Add Predecessor" }));
    const types = screen.getAllByLabelText("Type");
    await user.selectOptions(types[1], "SF");
    const lags = screen.getAllByLabelText("Lag");
    await user.clear(lags[1]);
    await user.type(lags[1], "3");
    await user.click(screen.getByRole("button", { name: "Save Planning" }));

    expect(onSubmit).toHaveBeenCalledWith(1, {
      duration: 0,
      is_milestone: true,
      constraint_type: "SNET",
      constraint_date: "2026-03-09",
      dependencies: [
        {
          predecessor_task_id: 2,
          dependency_type: "FF",
          lag_days: -2,
        },
        {
          predecessor_task_id: 3,
          dependency_type: "SF",
          lag_days: 3,
        },
      ],
    });
  });

  it("validates workday constraints and in-progress milestone conversion", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderDialog({
      task: { ...tasks[0], progress_status: "in_progress" },
      onSubmit,
    });

    await user.click(screen.getByRole("checkbox", { name: "Milestone" }));
    await user.selectOptions(screen.getByLabelText("Constraint"), "FNLT");
    await user.type(screen.getByLabelText("Constraint Date"), "2026-03-07");
    await user.click(screen.getByRole("button", { name: "Save Planning" }));

    expect(screen.getByText("In Progress tasks cannot be milestones."))
      .toBeInTheDocument();
    expect(screen.getByText("Constraint dates must be workdays."))
      .toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("removes dependencies and closes with Escape", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderDialog({
      task: {
        ...tasks[0],
        dependencies: [
          {
            predecessor_task_id: 2,
            dependency_type: "FS",
            lag_days: 0,
          },
        ],
      },
      onCancel,
    });

    await user.click(
      screen.getByRole("button", { name: "Remove predecessor 1" })
    );
    expect(screen.getByText("No predecessors")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("caps predecessor editing at the API limit", () => {
    const manyTasks = Array.from({ length: 52 }, (_, index) => ({
      id: index + 1,
      name: `Task ${index + 1}`,
      duration: 1,
    }));
    renderDialog({
      task: {
        ...manyTasks[0],
        dependencies: manyTasks.slice(1, 51).map((task) => ({
          predecessor_task_id: task.id,
          dependency_type: "FS",
          lag_days: 0,
        })),
      },
      tasks: manyTasks,
    });

    expect(screen.getByRole("button", { name: "Add Predecessor" }))
      .toBeDisabled();
  });
});
