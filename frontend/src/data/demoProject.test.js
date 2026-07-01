import { describe, expect, it } from "vitest";

import { buildDemoProject, DEMO_PROJECT_NAME } from "./demoProject";

const REFERENCE = new Date("2026-06-30T12:00:00");

describe("buildDemoProject", () => {
  it("produces a complete project blueprint", () => {
    const blueprint = buildDemoProject(REFERENCE);

    expect(blueprint.project.name).toBe(DEMO_PROJECT_NAME);
    expect(blueprint.companies.length).toBeGreaterThanOrEqual(4);
    expect(blueprint.tasks).toHaveLength(15);
    expect(blueprint.dailyLogs).toHaveLength(4);
    expect(blueprint.inspections).toHaveLength(3);
    expect(blueprint.notesDelays).toHaveLength(2);
    expect(blueprint.changeOrders).toHaveLength(2);
  });

  it("gives every task an explicit start date and positive duration", () => {
    const { tasks } = buildDemoProject(REFERENCE);

    for (const task of tasks) {
      expect(task.duration).toBeGreaterThan(0);
      expect(task.manual_start_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }

    // Schedule is anchored 21 days before the reference date.
    expect(tasks[0].manual_start_date).toBe("2026-06-09");
  });

  it("anchors record dates around the reference date", () => {
    const blueprint = buildDemoProject(REFERENCE);

    expect(blueprint.changeOrders.map((co) => co.co_number)).toEqual([
      "CO-101",
      "CO-102",
    ]);
    // CO-101 uses a -7 day offset from 2026-06-30.
    expect(blueprint.changeOrders[0].date).toBe("2026-06-23");
    expect(
      blueprint.notesDelays.some((entry) => entry.entry_type === "Delay")
    ).toBe(true);
  });

  it("returns fresh company objects (no shared references)", () => {
    const first = buildDemoProject(REFERENCE);
    const second = buildDemoProject(REFERENCE);

    expect(first.companies[0]).not.toBe(second.companies[0]);
    expect(first.companies[0]).toEqual(second.companies[0]);
  });
});
