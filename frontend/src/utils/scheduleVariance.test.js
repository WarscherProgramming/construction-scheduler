import { describe, expect, it } from "vitest";

import {
  formatComparisonStatus,
  formatCriticalChange,
  formatDurationVariance,
  formatScheduleDate,
  formatScheduleTimestamp,
  formatWorkdayVariance,
  getStructuralChanges,
} from "./scheduleVariance";


describe("schedule variance formatting", () => {
  it("formats directional workday and duration differences", () => {
    expect(formatWorkdayVariance(5)).toBe("5 workdays later");
    expect(formatWorkdayVariance(-1)).toBe("1 workday earlier");
    expect(formatWorkdayVariance(0)).toBe("No variance");
    expect(formatWorkdayVariance(null)).toBe("Unavailable");
    expect(formatDurationVariance(2)).toBe("2 days longer");
    expect(formatDurationVariance(-1)).toBe("1 day shorter");
  });

  it("formats dates, classifications, and structural changes factually", () => {
    expect(formatScheduleDate("2026-07-04")).toBe("07/04/2026");
    expect(formatScheduleDate("2026-02-31")).toBe("Unavailable");
    expect(formatScheduleDate("bad-date")).toBe("Unavailable");
    expect(formatScheduleTimestamp("2026-07-04")).toBe("Unavailable");
    expect(formatScheduleTimestamp("not-a-timestamp")).toBe("Unavailable");
    expect(formatComparisonStatus("removed")).toBe("Removed");
    expect(formatCriticalChange("newly_critical")).toBe("Newly critical");
    expect(
      getStructuralChanges({
        hierarchy_changed: true,
        dependency_changed: true,
        duration_changed: false,
        manual_start_changed: false,
        order_changed: true,
      })
    ).toEqual(["Hierarchy changed", "Dependency changed", "Order changed"]);
  });
});
