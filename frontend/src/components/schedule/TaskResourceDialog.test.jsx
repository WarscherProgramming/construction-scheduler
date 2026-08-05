import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TaskResourceDialog from "./TaskResourceDialog";


function resources(overrides = {}) {
  return {
    crews: [{ id: 1, name: "Electrical Crew", status: "active" }],
    equipment: [{ id: 2, name: "Lift 1", status: "active" }],
    assignments: [],
    isLoadingAssignments: false,
    isPending: vi.fn(() => false),
    loadAssignments: vi.fn().mockResolvedValue({ assignments: [] }),
    createAssignment: vi.fn().mockResolvedValue({ assignment: { id: 3 } }),
    updateAssignment: vi.fn().mockResolvedValue({ assignment: { id: 3 } }),
    deleteAssignment: vi.fn().mockResolvedValue({ message: "deleted" }),
    ...overrides,
  };
}

describe("TaskResourceDialog", () => {
  it("loads only the selected task and creates a whole-number assignment", async () => {
    const user = userEvent.setup();
    const state = resources();
    const onChanged = vi.fn();
    render(<TaskResourceDialog task={{ id: 9, name: "Rough-in" }} displayId="1.1" resources={state} onChanged={onChanged} onCancel={vi.fn()} />);
    await waitFor(() => expect(state.loadAssignments).toHaveBeenCalledWith(9));
    await user.selectOptions(screen.getByLabelText("Resource"), "1");
    await user.clear(screen.getByLabelText(/Allocation/));
    await user.type(screen.getByLabelText(/Allocation/), "3");
    await user.click(screen.getByRole("button", { name: "Assign Resource" }));
    expect(state.createAssignment).toHaveBeenCalledWith(9, {
      resource_type: "crew",
      resource_id: 1,
      allocation_amount: 3,
      notes: null,
    });
    expect(onChanged).toHaveBeenCalledOnce();
  });

  it("edits and confirms deletion without exposing resource reassignment", async () => {
    const user = userEvent.setup();
    const assignment = {
      id: 4,
      resource: { id: 1, name: "Electrical Crew", resource_type: "crew" },
      allocation_amount: 2,
      allocation_unit: "workers",
      notes: "Day shift",
    };
    const state = resources({ assignments: [assignment] });
    render(<TaskResourceDialog task={{ id: 9, name: "Rough-in" }} displayId="1.1" resources={state} onCancel={vi.fn()} />);
    const list = screen.getByRole("heading", { name: "Assigned resources" }).closest("section");
    await user.click(within(list).getByRole("button", { name: "Edit" }));
    expect(screen.queryByLabelText("Resource")).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText(/Allocation/));
    await user.type(screen.getByLabelText(/Allocation/), "4");
    await user.click(screen.getByRole("button", { name: "Save Assignment" }));
    expect(state.updateAssignment).toHaveBeenCalledWith(9, 4, expect.objectContaining({ allocation_amount: 4 }));
    await user.click(within(list).getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(state.deleteAssignment).toHaveBeenCalledWith(9, 4);
  });

  it("rejects fractional allocations in the client", async () => {
    const user = userEvent.setup();
    const state = resources();
    render(<TaskResourceDialog task={{ id: 9, name: "Rough-in" }} displayId="1.1" resources={state} onCancel={vi.fn()} />);
    await user.selectOptions(screen.getByLabelText("Resource"), "1");
    const amount = screen.getByLabelText(/Allocation/);
    await user.clear(amount);
    await user.type(amount, "1.5");
    fireEvent.submit(screen.getByRole("button", { name: "Assign Resource" }).closest("form"));
    expect(screen.getByRole("alert")).toHaveTextContent("whole allocation");
    expect(state.createAssignment).not.toHaveBeenCalled();
  });
});
