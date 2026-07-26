import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatScheduleImpact,
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
});
