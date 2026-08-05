import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ScheduleStartControl from "./ScheduleStartControl";


const settings = {
  project_id: 1,
  schedule_start_date: "2026-03-02",
  data_date: "2026-03-09",
};

function renderControl(props = {}) {
  return render(
    <ScheduleStartControl
      settings={settings}
      taskCount={3}
      onUpdate={vi.fn().mockResolvedValue(settings)}
      onUpdateDataDate={vi.fn().mockResolvedValue(settings)}
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
    expect(screen.getByLabelText("Data Date")).toHaveValue("2026-03-09");
    expect(
      screen.getByText(/Progress is current through this date/)
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

  it("validates the Data Date before issuing a request", async () => {
    const user = userEvent.setup();
    const onUpdateDataDate = vi.fn();
    renderControl({ onUpdateDataDate });

    const input = screen.getByLabelText("Data Date");
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Update Data Date" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid Data Date."
    );
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(onUpdateDataDate).not.toHaveBeenCalled();
  });

  it("confirms a Data Date change when progress exists and restores focus", async () => {
    const user = userEvent.setup();
    const onUpdateDataDate = vi.fn();
    renderControl({ statusedTaskCount: 2, onUpdateDataDate });

    const input = screen.getByLabelText("Data Date");
    await user.clear(input);
    await user.type(input, "2026-03-11");
    const updateButton = screen.getByRole("button", {
      name: "Update Data Date",
    });
    await user.click(updateButton);

    expect(
      screen.getByRole("alertdialog", { name: "Change Data Date?" })
    ).toHaveTextContent("2 statused tasks");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(updateButton).toHaveFocus();
    expect(onUpdateDataDate).not.toHaveBeenCalled();
  });

  it("updates the Data Date and rolls back a recoverable failure", async () => {
    const user = userEvent.setup();
    const onUpdateDataDate = vi.fn().mockResolvedValue(undefined);
    renderControl({ statusedTaskCount: 0, onUpdateDataDate });

    const input = screen.getByLabelText("Data Date");
    await user.clear(input);
    await user.type(input, "2026-03-11");
    await user.click(screen.getByRole("button", { name: "Update Data Date" }));

    await waitFor(() => {
      expect(onUpdateDataDate).toHaveBeenCalledWith("2026-03-11");
    });
    expect(input).toHaveValue("2026-03-09");
  });

  it("shows loading and pending states without fake headings", () => {
    const { rerender } = render(
      <ScheduleStartControl
        settings={null}
        taskCount={0}
        isLoading
        onUpdate={vi.fn()}
        onUpdateDataDate={vi.fn()}
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
        onUpdateDataDate={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Update Schedule Start" }))
      .toBeDisabled();
    expect(screen.getByRole("button", { name: "Update Data Date" }))
      .toBeDisabled();
  });
});
