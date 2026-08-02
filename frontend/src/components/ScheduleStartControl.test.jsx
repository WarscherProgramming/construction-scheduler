import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ScheduleStartControl from "./ScheduleStartControl";


const settings = {
  project_id: 1,
  schedule_start_date: "2026-03-02",
};

function renderControl(props = {}) {
  return render(
    <ScheduleStartControl
      settings={settings}
      taskCount={3}
      onUpdate={vi.fn().mockResolvedValue(settings)}
      {...props}
    />
  );
}


describe("ScheduleStartControl", () => {
  it("displays the persistent schedule start with visible impact help", () => {
    renderControl();

    expect(screen.getByLabelText("Schedule Start Date")).toHaveValue(
      "2026-03-02"
    );
    expect(
      screen.getByText("Changing this date recalculates unanchored root tasks.")
    ).toBeInTheDocument();
  });

  it("validates the date before opening confirmation", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    renderControl({ onUpdate });

    const input = screen.getByLabelText("Schedule Start Date");
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Update Schedule Start" }));

    expect(screen.getByText("Enter a valid Schedule Start Date.")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("confirms recalculation and restores focus when cancelled", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    renderControl({ onUpdate });

    const input = screen.getByLabelText("Schedule Start Date");
    await user.clear(input);
    await user.type(input, "2026-04-06");
    const updateButton = screen.getByRole("button", {
      name: "Update Schedule Start",
    });
    await user.click(updateButton);

    expect(
      screen.getByRole("alertdialog", { name: "Change Schedule Start Date?" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onUpdate).not.toHaveBeenCalled();
    expect(updateButton).toHaveFocus();
  });

  it("applies a confirmed change", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockResolvedValue({
      ...settings,
      schedule_start_date: "2026-04-06",
    });
    renderControl({ onUpdate });

    const input = screen.getByLabelText("Schedule Start Date");
    await user.clear(input);
    await user.type(input, "2026-04-06");
    await user.click(screen.getByRole("button", { name: "Update Schedule Start" }));
    await user.click(
      screen.getByRole("button", { name: "Recalculate Schedule" })
    );

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith("2026-04-06");
    });
  });

  it("updates without confirmation for an empty schedule and rolls back failure", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    renderControl({ taskCount: 0, onUpdate });

    const input = screen.getByLabelText("Schedule Start Date");
    await user.clear(input);
    await user.type(input, "2026-04-06");
    await user.click(screen.getByRole("button", { name: "Update Schedule Start" }));

    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith("2026-04-06"));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(input).toHaveValue("2026-03-02");
  });

  it("shows loading and pending states without fake headings", () => {
    const { rerender } = render(
      <ScheduleStartControl
        settings={null}
        taskCount={0}
        isLoading
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading schedule settings..."
    );

    rerender(
      <ScheduleStartControl
        settings={settings}
        taskCount={0}
        isUpdating
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Updating..." })).toBeDisabled();
  });
});
