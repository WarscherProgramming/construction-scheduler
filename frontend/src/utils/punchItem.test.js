import { describe, expect, it } from "vitest";

import { isPunchItemOverdue } from "./punchItem";

const TODAY = new Date(2026, 6, 25, 12);

describe("punch item utilities", () => {
  it("marks only active items with past due dates as overdue", () => {
    for (const status of ["Open", "In Progress"]) {
      expect(
        isPunchItemOverdue({ status, due_date: "2026-07-24" }, TODAY)
      ).toBe(true);
    }

    expect(
      isPunchItemOverdue(
        { status: "Open", due_date: "2026-07-25" },
        TODAY
      )
    ).toBe(false);
    expect(
      isPunchItemOverdue({ status: "Open", due_date: null }, TODAY)
    ).toBe(false);
  });

  it("excludes completed and verified items from overdue treatment", () => {
    for (const status of ["Completed", "Verified"]) {
      expect(
        isPunchItemOverdue({ status, due_date: "2026-07-24" }, TODAY)
      ).toBe(false);
    }
  });
});
