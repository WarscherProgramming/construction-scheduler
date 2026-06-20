import { describe, expect, it } from "vitest";

import { getDashboardMetrics } from "./dashboard";


describe("getDashboardMetrics", () => {
  it("summarizes schedule, delay, and pending change-order exposure", () => {
    expect(
      getDashboardMetrics({
        tasks: [
          { id: 1, start_date: "2026-06-20", end_date: "2026-06-21" },
          { id: 2, start_date: null, end_date: null },
        ],
        tasksThisWeek: [{ id: 1 }],
        projectDelays: [{ id: 3 }, { id: 4 }],
        changeOrders: [
          { status: "Pending", amount: "$1,250.50" },
          { status: "Pending", amount: "bad value" },
          { status: "Approved", amount: "500" },
        ],
      })
    ).toEqual({
      totalTasks: 2,
      scheduledTasks: 1,
      tasksThisWeek: 1,
      recordedDelays: 2,
      pendingChangeOrders: 2,
      pendingChangeOrderValue: 1250.5,
    });
  });
});
