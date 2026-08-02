import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ScheduleBaselineControl from "./ScheduleBaselineControl";


const activeBaseline = {
  id: 4,
  name: "Contract Baseline",
  status: "active",
  captured_at: "2026-07-02T15:00:00Z",
};
const archivedBaseline = {
  id: 3,
  name: "Bid Baseline",
  status: "archived",
  captured_at: "2026-06-01T15:00:00Z",
};


function props(overrides = {}) {
  return {
    scheduleStartDate: "2026-07-01",
    taskCount: 8,
    baselines: {
      baselines: [],
      selectedBaseline: null,
      viewBaselineId: null,
      listError: null,
      mutationError: null,
      isLoadingList: false,
      isCreating: false,
      isArchiving: false,
      isSelecting: false,
      requiresSelection: false,
      retryBaselines: vi.fn(),
      createBaseline: vi.fn(),
      archiveBaseline: vi.fn(),
      selectBaseline: vi.fn(),
      clearMutationError: vi.fn(),
      ...overrides,
    },
  };
}


describe("ScheduleBaselineControl", () => {
  it("shows an empty state and opens the create dialog", async () => {
    const user = userEvent.setup();
    const baselineProps = props();
    const { rerender } = render(
      <ScheduleBaselineControl {...baselineProps} isScheduleLoading />
    );

    expect(screen.getByText(/No baselines have been captured/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create Baseline" })
    ).toBeDisabled();
    rerender(<ScheduleBaselineControl {...baselineProps} />);
    await user.click(screen.getByRole("button", { name: "Create Baseline" }));
    expect(screen.getByRole("dialog", { name: "Capture Schedule Baseline" })).toBeInTheDocument();
  });

  it("groups active and archived baselines and loads a selection", async () => {
    const user = userEvent.setup();
    const selectBaseline = vi.fn();
    render(
      <ScheduleBaselineControl
        {...props({
          baselines: [activeBaseline, archivedBaseline],
          selectedBaseline: activeBaseline,
          viewBaselineId: 4,
          selectBaseline,
        })}
      />
    );

    expect(screen.getByRole("group", { name: "Active baselines" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Archived baselines" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Comparison baseline"), "3");
    expect(selectBaseline).toHaveBeenCalledWith("3");
  });

  it("names the selected baseline in archive confirmation", async () => {
    const user = userEvent.setup();
    const archiveBaseline = vi.fn().mockResolvedValue({ baseline: archivedBaseline });
    render(
      <ScheduleBaselineControl
        {...props({
          baselines: [activeBaseline],
          selectedBaseline: activeBaseline,
          viewBaselineId: 4,
          archiveBaseline,
        })}
      />
    );

    await user.click(screen.getByRole("button", { name: "Archive Baseline" }));
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveAccessibleName(
      "Archive Contract Baseline?"
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Archive Baseline" })
    );
    expect(archiveBaseline).toHaveBeenCalledWith(4);
  });

  it("offers a local retry after list failure", async () => {
    const user = userEvent.setup();
    const retryBaselines = vi.fn();
    render(
      <ScheduleBaselineControl
        {...props({ listError: new Error("offline"), retryBaselines })}
      />
    );

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(retryBaselines).toHaveBeenCalledOnce();
  });
});
