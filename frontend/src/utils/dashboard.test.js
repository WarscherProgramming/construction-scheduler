import { describe, expect, it } from "vitest";

import {
  getAttentionActivities,
  getChangeOrderTotalsByCompany,
  getDashboardMetrics,
  getInspectionIssueCount,
  getProjectHealthScore,
  getRecentActivity,
  getScheduleHealth,
  getThisWeekProgress,
  getTodaysFocus,
  getUpcomingInspections,
  getUpcomingTasks,
} from "./dashboard";

const REFERENCE = new Date("2026-06-30T09:00:00");

const TASKS = [
  { id: 1, name: "Sitework", start_date: "2026-06-20", end_date: "2026-06-25" },
  { id: 2, name: "Foundations", start_date: "2026-06-28", end_date: "2026-07-03" },
  { id: 3, name: "Steel", start_date: "2026-06-30", end_date: "2026-07-05" },
  { id: 4, name: "Roofing", start_date: "2026-07-06", end_date: "2026-07-10" },
  { id: 5, name: "Backlog", start_date: null, end_date: null },
];

const INSPECTIONS = [
  { id: 1, date: "2026-06-30", inspection_type: "Framing", status: "Pending" },
  { id: 2, date: "2026-06-25", inspection_type: "Footing", status: "Pass" },
  { id: 3, date: "2026-07-02", inspection_type: "Fire", status: "Pending" },
];


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

describe("getScheduleHealth", () => {
  it("reports timeline position and task states", () => {
    const health = getScheduleHealth(TASKS, REFERENCE);

    expect(health.hasSchedule).toBe(true);
    expect(health.projectStart).toBe("2026-06-20");
    expect(health.projectEnd).toBe("2026-07-10");
    expect(health.timelineElapsedPct).toBe(50);
    expect(health.activeCount).toBe(2);
    expect(health.pastDueCount).toBe(1);
    expect(health.upcomingCount).toBe(1);
    expect(health.startingTodayCount).toBe(1);
    expect(health.nextTask.id).toBe(4);
  });

  it("handles an unscheduled project", () => {
    expect(getScheduleHealth([], REFERENCE)).toMatchObject({
      hasSchedule: false,
      timelineElapsedPct: 0,
      nextTask: null,
    });
  });
});

describe("getThisWeekProgress", () => {
  it("counts tasks starting, finishing, and active this week", () => {
    expect(getThisWeekProgress(TASKS, REFERENCE)).toEqual({
      starting: 2,
      finishing: 1,
      active: 2,
    });
  });
});

describe("getUpcomingTasks", () => {
  it("returns future tasks within the horizon", () => {
    const upcoming = getUpcomingTasks(TASKS, REFERENCE, { days: 14, limit: 5 });
    expect(upcoming.map((task) => task.id)).toEqual([4]);
  });
});

describe("getAttentionActivities", () => {
  it("lists overdue first, then active", () => {
    const attention = getAttentionActivities(TASKS, REFERENCE);
    expect(attention.map((task) => [task.id, task.attention])).toEqual([
      [1, "overdue"],
      [2, "active"],
      [3, "active"],
    ]);
  });
});

describe("getUpcomingInspections", () => {
  it("keeps upcoming or pending inspections, sorted by date", () => {
    const upcoming = getUpcomingInspections(INSPECTIONS, REFERENCE);
    expect(upcoming.map((inspection) => inspection.id)).toEqual([1, 3]);
  });
});

describe("getTodaysFocus", () => {
  it("summarizes what to tackle first today", () => {
    const focus = getTodaysFocus({
      tasks: TASKS,
      inspections: INSPECTIONS,
      notesDelays: [{ entry_type: "Delay" }, { entry_type: "Note" }],
      changeOrders: [{ status: "Pending" }, { status: "Approved" }],
      referenceDate: REFERENCE,
    });

    expect(focus.startingTodayCount).toBe(1);
    expect(focus.inspectionsDueTodayCount).toBe(1);
    expect(focus.activeDelays).toBe(1);
    expect(focus.pendingChangeOrders).toBe(1);
    expect(focus.itemCount).toBe(4);
    expect(focus.hasItems).toBe(true);
  });
});

describe("getProjectHealthScore", () => {
  it("applies the weighted heuristic and bands the result", () => {
    expect(
      getProjectHealthScore({
        activeDelays: 1,
        pendingChangeOrders: 1,
        inspectionIssues: 2,
        pastDueActivities: 1,
      })
    ).toEqual({ score: 71, band: "at-risk" });

    expect(getProjectHealthScore({}).band).toBe("healthy");
    expect(
      getProjectHealthScore({ activeDelays: 5, pastDueActivities: 5 }).band
    ).toBe("critical");
  });
});

describe("getInspectionIssueCount", () => {
  it("counts pending, failed, and partial inspections", () => {
    expect(getInspectionIssueCount(INSPECTIONS)).toBe(2);
  });
});

describe("getChangeOrderTotalsByCompany", () => {
  it("sums amounts per company", () => {
    expect(
      getChangeOrderTotalsByCompany([
        { company: "Alpha", amount: "$1,000" },
        { company: "Alpha", amount: "500" },
        { company: "Beta", amount: "250" },
      ])
    ).toEqual([
      { company: "Alpha", total: 1500 },
      { company: "Beta", total: 250 },
    ]);
  });
});

describe("getRecentActivity", () => {
  it("merges records into a reverse-chronological feed and flags new items", () => {
    const feed = getRecentActivity(
      {
        dailyLogs: [{ id: 1, date: "2026-06-29", company: "X", manpower: 5 }],
        inspections: INSPECTIONS,
        changeOrders: [
          { id: 1, date: "2026-06-28", co_number: "CO-1", status: "Pending", company: "Y" },
        ],
        notesDelays: [
          { id: 1, date: "2026-06-27", entry_type: "Delay", company: "Z", description: "Rain" },
        ],
      },
      REFERENCE
    );

    expect(feed[0].date).toBe("2026-07-02");
    expect(feed).toHaveLength(6);
    expect(feed.find((item) => item.date === "2026-06-29").isNew).toBe(true);
    expect(feed.find((item) => item.date === "2026-06-28").isNew).toBe(false);
  });
});
