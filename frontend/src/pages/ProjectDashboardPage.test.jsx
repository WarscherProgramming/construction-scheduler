import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ProjectDashboardPage from "./ProjectDashboardPage";


describe("ProjectDashboardPage", () => {
  it("routes frequent field actions to their workflows", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    render(
      <ProjectDashboardPage
        projectName="North Ridge"
        tasksThisWeek={[]}
        changeOrderTotals={[]}
        projectDelays={[]}
        formatDate={(value) => value}
        onNavigate={onNavigate}
      />
    );

    await user.click(screen.getByRole("button", { name: "Add Daily Log" }));
    await user.click(screen.getByRole("button", { name: "Report Delay" }));
    await user.click(screen.getByRole("button", { name: "Add Inspection" }));
    await user.click(screen.getByRole("button", { name: "Add Change Order" }));

    expect(onNavigate.mock.calls).toEqual([
      ["dailyLogs"],
      ["notesDelays"],
      ["inspections"],
      ["changeOrders"],
    ]);
  });
});
