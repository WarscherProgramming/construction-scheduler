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
  rfis: [
    { id: 1, status: "Open", due_date: "2026-06-29" },
    { id: 2, status: "Pending", due_date: "2026-07-05" },
    { id: 3, status: "Closed", due_date: "2026-06-20" },
  ],
  submittals: [
    { id: 1, status: "Draft", required_by_date: "2026-06-29" },
    { id: 2, status: "Submitted", required_by_date: "2026-07-05" },
    { id: 3, status: "Under Review", required_by_date: "2026-06-28" },
    { id: 4, status: "Approved", required_by_date: "2026-06-20" },
    {
      id: 5,
      status: "Revise and Resubmit",
      required_by_date: "2026-06-20",
    },
    { id: 6, status: "Rejected", required_by_date: "2026-06-20" },
  ],
  punchItems: [
    { id: 1, status: "Open", due_date: "2026-06-29" },
    { id: 2, status: "In Progress", due_date: "2026-06-28" },
    { id: 3, status: "Open", due_date: "2026-07-05" },
    { id: 4, status: "Completed", due_date: "2026-06-20" },
    { id: 5, status: "Verified", due_date: "2026-06-20" },
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
    // Exposure appears in the KPI tile and the change-order bar list.
    expect(screen.getAllByText("$12,500").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", {
        name: "RFI health: 2 open, 1 overdue, 1 closed",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Submittal health: 3 active, 2 overdue, 1 approved",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Punch List health: 3 open, 2 overdue, 2 completed",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Open Punch Items")).toBeInTheDocument();
    expect(screen.getByText("2 overdue · 2 completed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open Schedule" }));
    expect(onNavigate).toHaveBeenCalledWith("scheduler");

    await user.click(screen.getByRole("button", { name: "Add Daily Log" }));
    await user.click(screen.getByRole("button", { name: "Report Delay" }));
    await user.click(screen.getByRole("button", { name: "Add Inspection" }));
    await user.click(screen.getByRole("button", { name: "Add Change Order" }));
    await user.click(
      screen.getByRole("button", {
        name: "RFI health: 2 open, 1 overdue, 1 closed",
      })
    );
    await user.click(
      screen.getByRole("button", {
        name: "Submittal health: 3 active, 2 overdue, 1 approved",
      })
    );
    await user.click(
      screen.getByRole("button", {
        name: "Punch List health: 3 open, 2 overdue, 2 completed",
      })
    );

    expect(onNavigate.mock.calls).toEqual([
      ["scheduler"],
      ["dailyLogs"],
      ["notesDelays"],
      ["inspections"],
      ["changeOrders"],
      ["rfis"],
      ["submittals"],
      ["punchItems"],
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
        isLoadingRFIs
        isLoadingSubmittals
        isLoadingPunchItems
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
    expect(
      screen.getByRole("button", { name: "RFI health, loading" })
    ).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", { name: "Submittal health, loading" })
    ).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", { name: "Punch List health, loading" })
    ).toHaveAttribute("aria-busy", "true");
  });

  it("shows zeroed record health without changing the empty dashboard", () => {
    render(<ProjectDashboardPage {...baseProps} />);

    expect(
      screen.getByRole("button", {
        name: "RFI health: 0 open, 0 overdue, 0 closed",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Submittal health: 0 active, 0 overdue, 0 approved",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Punch List health: 0 open, 0 overdue, 0 completed",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("No recent activity")).toBeInTheDocument();
  });

  it("isolates Submittal loading from unrelated dashboard controls", () => {
    render(
      <ProjectDashboardPage
        {...baseProps}
        {...populated}
        isLoadingSubmittals
      />
    );

    expect(
      screen.getByRole("button", { name: "Submittal health, loading" })
    ).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", {
        name: "RFI health: 2 open, 1 overdue, 1 closed",
      })
    ).not.toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
  });

  it("isolates Punch List loading from unrelated dashboard controls", () => {
    render(
      <ProjectDashboardPage
        {...baseProps}
        {...populated}
        isLoadingPunchItems
      />
    );

    expect(
      screen.getByRole("button", { name: "Punch List health, loading" })
    ).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", {
        name: "Submittal health: 3 active, 2 overdue, 1 approved",
      })
    ).not.toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
  });
});
