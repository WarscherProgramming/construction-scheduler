import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import UpcomingSchedule from "./UpcomingSchedule";


function upcomingTask(overrides = {}) {
  return {
    id: 1,
    name: "Install storefront",
    start_date: "2026-07-29",
    end_date: "2026-08-02",
    duration: 5,
    ...overrides,
  };
}


describe("UpcomingSchedule", () => {
  it("renders backend order, date-only values, and supplied durations", () => {
    render(
      <UpcomingSchedule
        tasks={[
          upcomingTask({ id: 3, name: "Third in schedule", duration: 1 }),
          upcomingTask({ id: 1, name: "First by ID", duration: 2 }),
        ]}
        hasScheduleTasks
        projectId={5}
        onNavigate={vi.fn()}
      />
    );

    const rows = screen.getAllByRole("listitem");
    expect(
      rows.map((row) => within(row).getByRole("heading").textContent)
    ).toEqual(["Third in schedule", "First by ID"]);
    expect(within(rows[0]).getByText("July 29, 2026")).toHaveAttribute(
      "datetime",
      "2026-07-29"
    );
    expect(within(rows[0]).getByText("August 2, 2026")).toHaveAttribute(
      "datetime",
      "2026-08-02"
    );
    expect(within(rows[0]).getByText("1 day")).toBeInTheDocument();
    expect(within(rows[1]).getByText("2 days")).toBeInTheDocument();
  });

  it("omits missing optional dates, durations, and unsupported critical fields", () => {
    render(
      <UpcomingSchedule
        tasks={[
          upcomingTask({
            end_date: null,
            duration: null,
            is_critical: true,
            total_float: 2,
          }),
        ]}
        hasScheduleTasks
        projectId={5}
        onNavigate={vi.fn()}
      />
    );

    const row = screen.getByRole("listitem");
    expect(screen.getByText("Starts")).toBeInTheDocument();
    expect(screen.queryByText("Ends")).not.toBeInTheDocument();
    expect(within(row).queryByText(/\b\d+\s+days?\b/)).not.toBeInTheDocument();
    expect(screen.queryByText(/critical path|total float/i)).not.toBeInTheDocument();
  });

  it("links to the Schedule page without a deep record target", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(
      <UpcomingSchedule
        tasks={[upcomingTask()]}
        hasScheduleTasks
        projectId={41}
        onNavigate={onNavigate}
      />
    );

    const link = screen.getByRole("link", {
      name: "View Schedule for upcoming task Install storefront",
    });
    await user.tab();
    expect(link).toHaveFocus();
    expect(link).toHaveAttribute("href", "#/projects/41/schedule");
    await user.click(link);
    expect(onNavigate).toHaveBeenCalledWith("scheduler");
  });

  it("distinguishes a quiet window from a project with no schedule", () => {
    const { rerender } = render(
      <UpcomingSchedule
        tasks={[]}
        hasScheduleTasks
        projectId={5}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByText(
        "No tasks are scheduled to start in the next seven days."
      )
    ).toBeInTheDocument();

    rerender(
      <UpcomingSchedule
        tasks={[]}
        hasScheduleTasks={false}
        projectId={5}
        onNavigate={vi.fn()}
      />
    );
    expect(
      screen.getByText(
        "No schedule tasks have been added to this project."
      )
    ).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("fails safely for missing names and invalid date values", () => {
    render(
      <UpcomingSchedule
        tasks={[
          upcomingTask({
            id: 12,
            name: null,
            start_date: "2026-02-31",
            end_date: "invalid",
          }),
        ]}
        hasScheduleTasks
        projectId={5}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Task 12" })
    ).toBeInTheDocument();
    expect(screen.queryByRole("time")).not.toBeInTheDocument();
    expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument();
  });
});
