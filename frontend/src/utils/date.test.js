import { describe, expect, it } from "vitest";

import { sortByDateDescending, toLocalDateInputValue } from "./date";


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
});
