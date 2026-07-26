import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatScheduleImpact,
  getChangeOrderMetrics,
  normalizeMoneyInput,
  normalizeOptionalValue,
  normalizeScheduleImpact,
  validateChangeOrderForm,
  validateLifecycleDates,
} from "./changeOrder";

describe("change order utilities", () => {
  it("formats dollar values without floating-point calculations", () => {
    expect(formatCurrency("0")).toBe("$0.00");
    expect(formatCurrency("1250")).toBe("$1,250.00");
    expect(formatCurrency("125000.50")).toBe("$125,000.50");
    expect(formatCurrency(null)).toBe("Not specified");
  });

  it("normalizes valid money and rejects negative or malformed values", () => {
    expect(normalizeMoneyInput(" 0.00 ")).toBe("0.00");
    expect(normalizeMoneyInput("125.5")).toBe("125.5");
    expect(normalizeMoneyInput("")).toBeNull();
    expect(normalizeMoneyInput("-1")).toBeUndefined();
    expect(normalizeMoneyInput("money")).toBeUndefined();
    expect(normalizeMoneyInput("1.234")).toBeUndefined();
  });

  it("normalizes and formats positive, zero, negative, and null impact", () => {
    expect(normalizeScheduleImpact("5")).toBe(5);
    expect(normalizeScheduleImpact("0")).toBe(0);
    expect(normalizeScheduleImpact("-2")).toBe(-2);
    expect(normalizeScheduleImpact("1.5")).toBeUndefined();
    expect(formatScheduleImpact(5)).toBe("+5 days");
    expect(formatScheduleImpact(0)).toBe("0 days");
    expect(formatScheduleImpact(-2)).toBe("-2 days");
    expect(formatScheduleImpact(null)).toBe("Not specified");
  });

  it("normalizes optional text without changing meaningful content", () => {
    expect(normalizeOptionalValue("  Desert Concrete  ")).toBe(
      "Desert Concrete"
    );
    expect(normalizeOptionalValue("   ")).toBeNull();
    expect(normalizeOptionalValue(null)).toBeNull();
  });

  it("validates every adjacent lifecycle date pair", () => {
    expect(
      validateLifecycleDates({
        requestedDate: "2026-07-20",
        submittedDate: "2026-07-21",
        approvedDate: "2026-07-22",
        executedDate: "2026-07-23",
      })
    ).toBeNull();
    expect(
      validateLifecycleDates({
        requestedDate: "2026-07-20",
        submittedDate: "",
        approvedDate: "2026-07-22",
        executedDate: "",
      })
    ).toBeNull();

    const invalidPairs = [
      {
        requestedDate: "2026-07-21",
        submittedDate: "2026-07-20",
      },
      {
        submittedDate: "2026-07-22",
        approvedDate: "2026-07-21",
      },
      {
        approvedDate: "2026-07-23",
        executedDate: "2026-07-22",
      },
    ];

    for (const dates of invalidPairs) {
      expect(validateLifecycleDates(dates)).toMatch(
        /cannot be earlier/
      );
    }
  });

  it("validates required content, money, and whole-day impact", () => {
    const valid = {
      date: "2026-07-26",
      title: "Title only",
      description: "",
      proposedAmount: "0",
      approvedAmount: "",
      scheduleImpactDays: "-2",
    };

    expect(validateChangeOrderForm(valid)).toBeNull();
    expect(
      validateChangeOrderForm({
        ...valid,
        title: "",
        description: "Description only",
      })
    ).toBeNull();
    expect(
      validateChangeOrderForm({ ...valid, title: "", description: "" })
    ).toMatch(/title or description/);
    expect(
      validateChangeOrderForm({ ...valid, proposedAmount: "-1" })
    ).toMatch(/Proposed amount/);
    expect(
      validateChangeOrderForm({ ...valid, scheduleImpactDays: "1.5" })
    ).toMatch(/whole number/);
  });

  it("counts every enhanced workflow status in the correct bucket", () => {
    const records = [
      "Draft",
      "Pending",
      "Submitted",
      "Under Review",
      "Approved",
      "Executed",
      "Rejected",
      "Void",
      "Unknown Legacy",
    ].map((status) => ({ status }));

    expect(getChangeOrderMetrics(records)).toMatchObject({
      activeChangeOrders: 4,
      approvedChangeOrders: 2,
      rejectedChangeOrders: 2,
    });
  });

  it("sums proposed cost with exact legacy fallback and no double count", () => {
    expect(
      getChangeOrderMetrics([
        { proposed_amount: "0.10", amount: "999" },
        { proposed_amount: "0.20" },
        { proposed_amount: "100.00", amount: "500" },
        { proposed_amount: null, amount: "$1,250.50" },
        { proposed_amount: null, amount: "bad value" },
        { proposed_amount: null, amount: "-10" },
        { proposed_amount: null, amount: "0" },
      ]).proposedCost
    ).toBe("1350.80");
  });

  it("sums only approved amounts with two-decimal precision", () => {
    expect(
      getChangeOrderMetrics([
        { approved_amount: "0.10", proposed_amount: "500" },
        { approved_amount: "0.20", amount: "400" },
        { approved_amount: "0" },
        { approved_amount: null, proposed_amount: "900", amount: "800" },
      ]).approvedCost
    ).toBe("0.30");
  });

  it("sums valid schedule impacts and ignores malformed values", () => {
    expect(
      getChangeOrderMetrics([
        { schedule_impact_days: 5 },
        { schedule_impact_days: -2 },
        { schedule_impact_days: 0 },
        { schedule_impact_days: null },
        { schedule_impact_days: "1.5" },
        { schedule_impact_days: "not-days" },
      ]).scheduleImpactDays
    ).toBe(3);
  });

  it("returns zeroed metrics for an empty collection", () => {
    expect(getChangeOrderMetrics()).toEqual({
      activeChangeOrders: 0,
      approvedChangeOrders: 0,
      rejectedChangeOrders: 0,
      proposedCost: "0.00",
      approvedCost: "0.00",
      scheduleImpactDays: 0,
    });
  });
});
