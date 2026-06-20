import { DndContext } from "@dnd-kit/core";
import { SortableContext } from "@dnd-kit/sortable";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SortableTaskRow from "./SortableTaskRow";


const task = {
  id: 42,
  name: "Footings",
  duration: 2,
  start_date: "2026-06-22",
  end_date: "2026-06-23",
  predecessor: "10+1",
  parent_task_id: 10,
  is_collapsed: 0,
};


function renderRow(overrides = {}) {
  const props = {
    task,
    index: 0,
    displayId: 1,
    displayPredecessor: "2+1",
    selectedTaskId: null,
    setSelectedTaskId: vi.fn(),
    editingCell: null,
    editValue: "",
    setEditValue: vi.fn(),
    handleCellClick: vi.fn(),
    handleCellSave: vi.fn(),
    handleCellCancel: vi.fn(),
    handleDelete: vi.fn(),
    handleToggleCollapse: vi.fn(),
    formatDate: (value) => value,
    hasChildren: true,
    depth: 1,
    ...overrides,
  };

  render(
    <DndContext>
      <table>
        <tbody>
          <SortableContext items={[task.id]}>
            <SortableTaskRow {...props} />
          </SortableContext>
        </tbody>
      </table>
    </DndContext>
  );

  return props;
}


describe("SortableTaskRow", () => {
  it("exposes editable cells and the drag handle to keyboard users", async () => {
    const user = userEvent.setup();
    const props = renderRow();

    expect(
      screen.getByRole("button", {
        name: "Reorder schedule task 1: Footings",
      })
    ).toBeInTheDocument();
    expect(screen.queryByText("Move")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Edit task 1 name" })
    );

    expect(props.setSelectedTaskId).toHaveBeenCalledWith(42);
    expect(props.handleCellClick).toHaveBeenCalledWith(task, "name");
  });

  it("dispatches deletion from the row action", async () => {
    const user = userEvent.setup();
    const props = renderRow();

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(props.handleDelete).toHaveBeenCalledWith(42);
  });

  it("opens the predecessor editor and saves on blur", async () => {
    const user = userEvent.setup();
    const handleCellSave = vi.fn();
    const setEditValue = vi.fn();

    renderRow({
      editingCell: { id: 42, field: "predecessor" },
      editValue: "10SS+2",
      handleCellSave,
      setEditValue,
    });

    const input = screen.getByPlaceholderText(
      "Schedule ID: 1, 1+3, 1SS+4"
    );
    await user.clear(input);
    await user.type(input, "15");
    await user.tab();

    expect(setEditValue).toHaveBeenCalled();
    expect(handleCellSave).toHaveBeenCalledWith(task);
  });

  it("saves an edited cell with Enter", async () => {
    const user = userEvent.setup();
    const handleCellSave = vi.fn();

    renderRow({
      editingCell: { id: 42, field: "duration" },
      editValue: "4",
      handleCellSave,
    });

    await user.type(screen.getByLabelText("Task 1 duration"), "{enter}");

    expect(handleCellSave).toHaveBeenCalledOnce();
    expect(handleCellSave).toHaveBeenCalledWith(task);
  });

  it("cancels an edited cell with Escape without saving", async () => {
    const user = userEvent.setup();
    const handleCellSave = vi.fn();
    const handleCellCancel = vi.fn();

    renderRow({
      editingCell: { id: 42, field: "name" },
      editValue: "Footings",
      handleCellSave,
      handleCellCancel,
    });

    await user.type(screen.getByLabelText("Task 1 name"), "{escape}");

    expect(handleCellCancel).toHaveBeenCalledOnce();
    expect(handleCellSave).not.toHaveBeenCalled();
  });
});
