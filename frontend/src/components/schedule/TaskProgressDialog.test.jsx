import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TaskProgressDialog from "./TaskProgressDialog";


const task = {
  id: 7,
  name: "Install switchgear",
  duration: 5,
  progress_status: "not_started",
  percent_complete: 0,
  actual_start_date: null,
  actual_finish_date: null,
  remaining_duration: 5,
};

function renderDialog(props = {}) {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onCancel = vi.fn();
  const view = render(
    <TaskProgressDialog
      task={task}
      displayId="2.1"
      dataDate="2026-03-09"
      onSubmit={onSubmit}
      onCancel={onCancel}
      {...props}
    />
  );
  return { ...view, onSubmit, onCancel };
}


describe("TaskProgressDialog", () => {
  it("identifies the task, focuses status, traps focus, and restores it", async () => {
    const user = userEvent.setup();
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const { onCancel, unmount } = renderDialog();

    expect(
      screen.getByRole("dialog", { name: "Update Progress: Install switchgear" })
    ).toBeInTheDocument();
    expect(screen.getByText(/Task 2.1/)).toHaveTextContent("2026-03-09");
    expect(screen.getByLabelText("Progress Status")).toHaveFocus();

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("button", { name: "Update Progress" }))
      .toHaveFocus();
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();

    unmount();
    await waitFor(() => expect(opener).toHaveFocus());
    opener.remove();
  });

  it("shows and validates the In Progress fields", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    await user.selectOptions(
      screen.getByLabelText("Progress Status"),
      "in_progress"
    );
    expect(screen.getByLabelText("Actual Start")).toBeInTheDocument();
    expect(screen.getByLabelText("Percent Complete")).toBeInTheDocument();
    expect(screen.getByLabelText("Remaining Duration")).toBeInTheDocument();
    expect(screen.queryByLabelText("Actual Finish")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Actual Start"), "2026-03-10");
    await user.type(screen.getByLabelText("Percent Complete"), "100");
    await user.clear(screen.getByLabelText("Remaining Duration"));
    await user.type(screen.getByLabelText("Remaining Duration"), "0");
    await user.click(screen.getByRole("button", { name: "Update Progress" }));

    expect(screen.getAllByRole("alert")).toHaveLength(3);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a valid In Progress payload and preserves values after failure", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    await user.selectOptions(
      screen.getByLabelText("Progress Status"),
      "in_progress"
    );
    await user.type(screen.getByLabelText("Actual Start"), "2026-03-05");
    await user.type(screen.getByLabelText("Percent Complete"), "40");
    await user.clear(screen.getByLabelText("Remaining Duration"));
    await user.type(screen.getByLabelText("Remaining Duration"), "3");
    await user.click(screen.getByRole("button", { name: "Update Progress" }));

    expect(onSubmit).toHaveBeenCalledWith(7, {
      progress_status: "in_progress",
      actual_start_date: "2026-03-05",
      percent_complete: 40,
      remaining_duration: 3,
    });
    expect(screen.getByLabelText("Percent Complete")).toHaveValue(40);
    expect(screen.getByLabelText("Remaining Duration")).toHaveValue(3);
  });

  it("validates and submits completed actual dates", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    await user.selectOptions(
      screen.getByLabelText("Progress Status"),
      "completed"
    );
    await user.type(screen.getByLabelText("Actual Start"), "2026-03-06");
    await user.type(screen.getByLabelText("Actual Finish"), "2026-03-05");
    await user.click(screen.getByRole("button", { name: "Update Progress" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Actual Finish cannot be before Actual Start."
    );

    await user.clear(screen.getByLabelText("Actual Finish"));
    await user.type(screen.getByLabelText("Actual Finish"), "2026-03-08");
    await user.click(screen.getByRole("button", { name: "Update Progress" }));
    expect(onSubmit).toHaveBeenCalledWith(7, {
      progress_status: "completed",
      actual_start_date: "2026-03-06",
      actual_finish_date: "2026-03-08",
    });
  });

  it("requires confirmation before reversing completed work", async () => {
    const user = userEvent.setup();
    const completedTask = {
      ...task,
      progress_status: "completed",
      percent_complete: 100,
      actual_start_date: "2026-03-02",
      actual_finish_date: "2026-03-06",
      remaining_duration: 0,
    };
    const { onSubmit } = renderDialog({ task: completedTask });

    await user.selectOptions(
      screen.getByLabelText("Progress Status"),
      "not_started"
    );
    await user.click(screen.getByRole("button", { name: "Update Progress" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Field history is not retained."
    );
    expect(onSubmit).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Confirm Correction" }));
    expect(onSubmit).toHaveBeenCalledWith(7, {
      progress_status: "not_started",
    });
  });

  it("protects pending submission from cancellation and duplicate actions", async () => {
    const user = userEvent.setup();
    const { onCancel } = renderDialog({ isSubmitting: true });

    expect(screen.getByLabelText("Progress Status")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Updating..." })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(onCancel).not.toHaveBeenCalled();
  });
});
