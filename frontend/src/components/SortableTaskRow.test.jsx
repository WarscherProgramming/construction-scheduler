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
  predecessor: "10FS+1",
  parent_task_id: 10,
  is_collapsed: 0,
};


function renderRow(overrides = {}) {
  const props = {
    task,
    index: 0,
    selectedTaskId: null,
    setSelectedTaskId: vi.fn(),
    editingCell: null,
    editValue: "",
    setEditValue: vi.fn(),
    handleCellClick: vi.fn(),
    handleCellSave: vi.fn(),
    handleDelete: vi.fn(),
    handleIndent: vi.fn(),
    handleOutdent: vi.fn(),
    handleToggleCollapse: vi.fn(),
    formatDate: (value) => value,
    hasChildren: true,
    depth: 1,
    canIndent: true,
    canOutdent: true,
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
  it("dispatches hierarchy and deletion actions", async () => {
    const user = userEvent.setup();
    const props = renderRow();

    await user.click(screen.getByRole("button", { name: "Indent" }));
    await user.click(screen.getByRole("button", { name: "Outdent" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(props.handleIndent).toHaveBeenCalledWith(task);
    expect(props.handleOutdent).toHaveBeenCalledWith(task);
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
      "Task ID: 12, 12+3, 12SS+4"
    );
    await user.clear(input);
    await user.type(input, "15");
    await user.tab();

    expect(setEditValue).toHaveBeenCalled();
    expect(handleCellSave).toHaveBeenCalledWith(task);
  });
});
