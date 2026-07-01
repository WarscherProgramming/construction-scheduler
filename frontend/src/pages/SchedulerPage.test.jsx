import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SchedulerPage from "./SchedulerPage";


const baseProps = {
  tasks: [],
  templates: [],
  selectedProjectId: 1,
  selectedTaskId: null,
  editingCell: null,
  editValue: "",
  templateName: "",
  selectedTemplateId: "",
  scheduleView: "table",
  setSelectedTaskId: vi.fn(),
  setEditValue: vi.fn(),
  setTemplateName: vi.fn(),
  setSelectedTemplateId: vi.fn(),
  setScheduleView: vi.fn(),
  onNavigate: vi.fn(),
  onSaveTemplate: vi.fn(),
  onApplyTemplate: vi.fn(),
  onExport: vi.fn(),
  onLogout: vi.fn(),
  onDragEnd: vi.fn(),
  onCellClick: vi.fn(),
  onCellSave: vi.fn(),
  onCellCancel: vi.fn(),
  onDelete: vi.fn(),
  onIndent: vi.fn(),
  onOutdent: vi.fn(),
  onToggleCollapse: vi.fn(),
  getEmptyRow: () => ({ id: null, name: "" }),
  formatDate: (value) => value,
  taskHasChildren: () => false,
  isTaskHiddenByCollapsedParent: () => false,
  getTaskDepth: () => 0,
};


describe("SchedulerPage", () => {
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
});
