import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ScheduleHealthCard from "./ScheduleHealthCard";


const HEALTH = {
  category: "critical",
  summary: "Schedule is critical because unavailable resources affect planned work.",
  baseline: null,
  data_date: "2026-08-05",
  metrics: {
    project_finish_variance_workdays: null,
    blocked_look_ahead_items: 2,
    resource_overallocated_days: 4,
  },
  reasons: [{ code: "resource", label: "Resource conflict", severity: "critical", value: 1 }],
};

describe("ScheduleHealthCard", () => {
  it("shows textual health evidence and navigates to the scheduler", async () => {
    const onNavigate = vi.fn();
    render(<ScheduleHealthCard health={HEALTH} projectId={7} onNavigate={onNavigate} />);

    expect(screen.getByText("critical schedule health")).toBeInTheDocument();
    expect(screen.getByText(HEALTH.summary)).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "View Schedule Summary" });
    expect(link).toHaveAttribute("href", "#/projects/7/schedule");
    link.focus();
    expect(link).toHaveFocus();
    await userEvent.click(link);
    expect(onNavigate).toHaveBeenCalledWith("scheduler");
  });
});
