import { describe, expect, it } from "vitest";

import {
  formatDashboardCurrency,
  formatDashboardDate,
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
  });

  it("formats date-only values without UTC conversion", () => {
    expect(formatDashboardDate("2026-07-27")).toBe("July 27, 2026");
    expect(formatDashboardDate(null)).toBe("Date unavailable");
  });
});
