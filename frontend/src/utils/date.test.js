import { describe, expect, it } from "vitest";

import {
  addDays,
  formatDisplayDate,
  formatLocalDateForApi,
  getCurrentWeekRange,
  isPastLocalDate,
  parseLocalDateInputValue,
  sortByDateDescending,
  toLocalDateInputValue,
} from "./date";


describe("date utilities", () => {
  it("formats ISO dates for display and passes through everything else", () => {
    expect(formatDisplayDate("2026-06-20")).toBe("06/20/2026");
    expect(formatDisplayDate("06/20/2026")).toBe("06/20/2026");
    expect(formatDisplayDate(null)).toBe("-");
    expect(formatDisplayDate("")).toBe("-");
  });

  it("adds calendar days without mutating the input", () => {
    const start = new Date(2026, 5, 30);

    expect(addDays(start, 2).getDate()).toBe(2);
    expect(addDays(start, 2).getMonth()).toBe(6);
    expect(start.getDate()).toBe(30);
  });

  it("formats a date for native date inputs without UTC conversion", () => {
    const date = new Date(2026, 5, 20, 23, 30);

    expect(toLocalDateInputValue(date)).toBe("2026-06-20");
  });

  it("formats the local calendar date for API boundaries", () => {
    const nearUtcBoundary = new Date(2026, 0, 2, 23, 59, 59);

    expect(formatLocalDateForApi(nearUtcBoundary)).toBe("2026-01-02");
    expect(formatLocalDateForApi(new Date(2026, 8, 7, 1))).toBe(
      "2026-09-07"
    );
  });

  it("sorts records newest first and uses ID for same-day records", () => {
    const records = [
      { id: 1, date: "2026-06-18" },
      { id: 2, date: "2026-06-20" },
      { id: 3, date: "2026-06-20" },
    ];

    expect(sortByDateDescending(records).map((record) => record.id)).toEqual([
      3, 2, 1,
    ]);
    expect(records.map((record) => record.id)).toEqual([1, 2, 3]);
  });

  it("parses date input values in local time", () => {
    const parsed = parseLocalDateInputValue("2026-06-20");

    expect(parsed.getFullYear()).toBe(2026);
    expect(parsed.getMonth()).toBe(5);
    expect(parsed.getDate()).toBe(20);
  });

  it("rejects malformed and impossible date-only values", () => {
    expect(parseLocalDateInputValue("2026-02-31")).toBeNull();
    expect(parseLocalDateInputValue("2026-7-27")).toBeNull();
    expect(parseLocalDateInputValue("not-a-date")).toBeNull();
  });

  it("identifies ISO dates before the current local date", () => {
    const today = new Date(2026, 6, 25, 15);

    expect(isPastLocalDate("2026-07-24", today)).toBe(true);
    expect(isPastLocalDate("2026-07-25", today)).toBe(false);
    expect(isPastLocalDate(null, today)).toBe(false);
  });

  it("returns inclusive Sunday-through-Saturday week bounds", () => {
    const { start, end } = getCurrentWeekRange(new Date(2026, 5, 24, 15));

    expect(toLocalDateInputValue(start)).toBe("2026-06-21");
    expect(toLocalDateInputValue(end)).toBe("2026-06-27");
    expect(start.getHours()).toBe(0);
    expect(end.getHours()).toBe(23);
  });
});
