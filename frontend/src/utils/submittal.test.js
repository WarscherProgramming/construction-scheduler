import { describe, expect, it } from "vitest";

import { isSubmittalOverdue } from "./submittal";

const TODAY = new Date(2026, 6, 25, 12);

describe("submittal utilities", () => {
  it("marks unresolved records past their required-by date as overdue", () => {
    for (const status of ["Draft", "Submitted", "Under Review"]) {
      expect(
        isSubmittalOverdue(
          { status, required_by_date: "2026-07-24" },
          TODAY
        )
      ).toBe(true);
    }

    expect(
      isSubmittalOverdue(
        { status: "Submitted", required_by_date: "2026-07-25" },
        TODAY
      )
    ).toBe(false);
    expect(
      isSubmittalOverdue(
        { status: "Submitted", required_by_date: null },
        TODAY
      )
    ).toBe(false);
  });

  it("excludes every resolved status from overdue treatment", () => {
    for (const status of [
      "Approved",
      "Revise and Resubmit",
      "Rejected",
    ]) {
      expect(
        isSubmittalOverdue(
          { status, required_by_date: "2026-07-24" },
          TODAY
        )
      ).toBe(false);
    }
  });
});
