import { describe, expect, it } from "vitest";

import {
  calculateDistributionValue,
  formatDashboardCount,
  formatDashboardCurrency,
  formatDashboardDate,
  formatDashboardDuration,
  formatDashboardLinkContext,
  formatOptionalDashboardDate,
  formatDashboardTimestamp,
} from "./dashboardSummary";


describe("dashboard summary formatting", () => {
  it("formats backend decimal strings as US dollars", () => {
    expect(formatDashboardCurrency("0.00")).toBe("$0.00");
    expect(formatDashboardCurrency("100.30")).toBe("$100.30");
    expect(formatDashboardCurrency("1234567.89")).toBe("$1,234,567.89");
  });

  it("does not expose NaN for missing or invalid currency", () => {
    expect(formatDashboardCurrency(null)).toBe("Unavailable");
    expect(formatDashboardCurrency("invalid")).toBe("Unavailable");
    expect(formatDashboardCurrency("-0.01")).toBe("Unavailable");
  });

  it("formats date-only values without UTC conversion", () => {
    expect(formatDashboardDate("2026-07-27")).toBe("July 27, 2026");
    expect(formatDashboardDate(null)).toBe("Date unavailable");
    expect(formatOptionalDashboardDate("2026-07-27")).toBe(
      "July 27, 2026"
    );
    expect(formatOptionalDashboardDate("2026-02-31")).toBeNull();
  });

  it("formats supplied durations without calculating them", () => {
    expect(formatDashboardDuration(1)).toBe("1 day");
    expect(formatDashboardDuration(2)).toBe("2 days");
    expect(formatDashboardDuration(null)).toBeNull();
    expect(formatDashboardDuration("invalid")).toBeNull();
    expect(formatDashboardDuration(-1)).toBeNull();
    expect(formatDashboardDuration(1.5)).toBeNull();
  });

  it("formats aware timestamps in the user's local timezone", () => {
    const value = "2026-07-28T21:14:00Z";
    const expected = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));

    expect(formatDashboardTimestamp(value)).toBe(expected);
    const offsetValue = "2026-07-28T14:14:00-07:00";
    expect(formatDashboardTimestamp(offsetValue)).toBe(
      new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(offsetValue))
    );
    expect(formatDashboardTimestamp(null)).toBeNull();
    expect(formatDashboardTimestamp("invalid")).toBeNull();
    expect(formatDashboardTimestamp("2026-07-28")).toBeNull();
  });

  it("fails safely for unavailable aggregate counts", () => {
    expect(formatDashboardCount(0)).toBe(0);
    expect(formatDashboardCount(12)).toBe(12);
    expect(formatDashboardCount(null)).toBe("Unavailable");
    expect(formatDashboardCount(-1)).toBe("Unavailable");
    expect(formatDashboardCount(1.5)).toBe("Unavailable");
    expect(formatDashboardCount("invalid")).toBe("Unavailable");
  });

  it("clamps aggregate visual widths without changing visible counts", () => {
    expect(calculateDistributionValue(2, 8)).toBe(25);
    expect(calculateDistributionValue(12, 8)).toBe(100);
    expect(calculateDistributionValue(2, 0)).toBe(0);
    expect(calculateDistributionValue(-1, 8)).toBe(0);
    expect(calculateDistributionValue(1.5, 8)).toBe(0);
    expect(calculateDistributionValue(2, -8)).toBe(0);
    expect(calculateDistributionValue(null, 8)).toBe(0);
    expect(calculateDistributionValue("invalid", 8)).toBe(0);
  });

  it("keeps contextual link names concise", () => {
    expect(formatDashboardLinkContext("RFI-017", "RFI")).toBe("RFI-017");
    expect(formatDashboardLinkContext("", "RFI")).toBe("RFI");
    expect(formatDashboardLinkContext("A".repeat(80), "RFI")).toBe(
      `${"A".repeat(61)}...`
    );
  });
});
