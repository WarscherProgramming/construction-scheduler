import { render, screen } from "@testing-library/react";
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

    expect(screen.getByRole("columnheader", { name: "Id" })).toHaveClass(
      "schedule-sticky-0"
    );
    expect(screen.getByRole("columnheader", { name: "Task" })).toHaveClass(
      "schedule-sticky-1"
    );
  });
});
