import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ProjectDashboardPage from "./ProjectDashboardPage";

const REFERENCE = new Date("2026-06-30T09:00:00");

const baseProps = {
  projectName: "North Ridge",
  referenceDate: REFERENCE,
  formatDate: (value) => value,
  onNavigate: vi.fn(),
};

const populated = {
  tasks: [
    { id: 1, name: "Sitework", start_date: "2026-06-20", end_date: "2026-06-25" },
    { id: 2, name: "Foundations", start_date: "2026-06-30", end_date: "2026-07-05" },
    { id: 3, name: "Steel", start_date: "2026-07-06", end_date: "2026-07-10" },
  ],
  changeOrders: [
    {
      id: 1,
      date: "2026-06-28",
      co_number: "CO-102",
      company: "ClearView Glazing",
      status: "Pending",
      amount: "12500",
    },
  ],
  notesDelays: [
    {
      id: 1,
      date: "2026-06-25",
      entry_type: "Delay",
      company: "Desert Concrete",
      description: "Rain",
    },
  ],
  inspections: [
    { id: 1, date: "2026-06-30", inspection_type: "Framing", status: "Pending" },
  ],
  dailyLogs: [
    { id: 1, date: "2026-06-29", company: "Desert Concrete", manpower: 8 },
  ],
};

describe("ProjectDashboardPage", () => {
  it("surfaces today's focus, health, and routes frequent field actions", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    render(
      <ProjectDashboardPage {...baseProps} {...populated} onNavigate={onNavigate} />
    );

    // Today's Focus summary and Open Schedule action.
    expect(screen.getByText(/Today.s Focus/)).toBeInTheDocument();
    expect(screen.getByText(/4 items need/)).toBeInTheDocument();

    // Health gauge (score 77 → At Risk) and change-order exposure.
    expect(screen.getByText("77")).toBeInTheDocument();
    expect(screen.getByText("At Risk")).toBeInTheDocument();
    expect(screen.getByText("$12,500")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open Schedule" }));
    expect(onNavigate).toHaveBeenCalledWith("scheduler");

    await user.click(screen.getByRole("button", { name: "Add Daily Log" }));
    await user.click(screen.getByRole("button", { name: "Report Delay" }));
    await user.click(screen.getByRole("button", { name: "Add Inspection" }));
    await user.click(screen.getByRole("button", { name: "Add Change Order" }));

    expect(onNavigate.mock.calls).toEqual([
      ["scheduler"],
      ["dailyLogs"],
      ["notesDelays"],
      ["inspections"],
      ["changeOrders"],
    ]);
  });

  it("distinguishes loading dashboard data from empty data", () => {
    render(
      <ProjectDashboardPage
        {...baseProps}
        tasks={[]}
        changeOrders={[]}
        notesDelays={[]}
        inspections={[]}
        dailyLogs={[]}
        isLoadingTasks
        isLoadingChangeOrders
        isLoadingDelays
        isLoadingInspections
        isLoadingDailyLogs
      />
    );

    expect(
      screen.getByRole("region", { name: "Project Overview" })
    ).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText(/Loading today.s focus/)).toBeInTheDocument();
    expect(screen.getByText("Loading inspections…")).toBeInTheDocument();
    expect(screen.getByText("Loading daily logs…")).toBeInTheDocument();
    expect(
      screen.queryByText("You're all clear for today")
    ).not.toBeInTheDocument();
  });
});
