import { describe, expect, it } from "vitest";

import {
  getCurrentWeekRange,
  parseLocalDateInputValue,
  sortByDateDescending,
  toLocalDateInputValue,
} from "./date";


describe("date utilities", () => {
  it("formats a date for native date inputs without UTC conversion", () => {
    const date = new Date(2026, 5, 20, 23, 30);

    expect(toLocalDateInputValue(date)).toBe("2026-06-20");
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

  it("returns inclusive Sunday-through-Saturday week bounds", () => {
    const { start, end } = getCurrentWeekRange(new Date(2026, 5, 24, 15));

    expect(toLocalDateInputValue(start)).toBe("2026-06-21");
    expect(toLocalDateInputValue(end)).toBe("2026-06-27");
    expect(start.getHours()).toBe(0);
    expect(end.getHours()).toBe(23);
  });
});
