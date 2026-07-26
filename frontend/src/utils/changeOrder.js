export const CHANGE_ORDER_STATUSES = [
  "Draft",
  "Pending",
  "Submitted",
  "Under Review",
  "Approved",
  "Rejected",
  "Executed",
  "Void",
];

const MONEY_PATTERN = /^\d+(?:\.\d{1,2})?$/;
const LEGACY_MONEY_PATTERN =
  /^(?:\$\s*)?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?$/;
const WHOLE_NUMBER_PATTERN = /^-?\d+$/;
const ACTIVE_CHANGE_ORDER_STATUSES = new Set([
  "Draft",
  "Pending",
  "Submitted",
  "Under Review",
]);
const APPROVED_CHANGE_ORDER_STATUSES = new Set(["Approved", "Executed"]);
const REJECTED_CHANGE_ORDER_STATUSES = new Set(["Rejected", "Void"]);

function moneyToCents(value) {
  const normalized = String(value ?? "").trim();

  if (!MONEY_PATTERN.test(normalized)) return null;

  const [integerPart, decimalPart = ""] = normalized.split(".");
  return (
    BigInt(integerPart) * 100n +
    BigInt(decimalPart.padEnd(2, "0"))
  );
}

function legacyMoneyToCents(value) {
  const normalized = String(value ?? "").trim();

  if (!LEGACY_MONEY_PATTERN.test(normalized)) return null;

  return moneyToCents(normalized.replace(/[$,\s]/g, ""));
}

export function centsToDecimalString(cents) {
  const normalized = typeof cents === "bigint" ? cents : 0n;
  const dollars = normalized / 100n;
  const remainder = normalized % 100n;

  return `${dollars}.${remainder.toString().padStart(2, "0")}`;
}

export function getChangeOrderProposedCostCents(changeOrder) {
  const proposedAmount = String(
    changeOrder?.proposed_amount ?? ""
  ).trim();

  if (proposedAmount) {
    return moneyToCents(proposedAmount) ?? 0n;
  }

  return legacyMoneyToCents(changeOrder?.amount) ?? 0n;
}

export function getChangeOrderMetrics(changeOrders = []) {
  let proposedCostCents = 0n;
  let approvedCostCents = 0n;
  let scheduleImpactDays = 0;
  let activeChangeOrders = 0;
  let approvedChangeOrders = 0;
  let rejectedChangeOrders = 0;

  for (const changeOrder of changeOrders) {
    if (ACTIVE_CHANGE_ORDER_STATUSES.has(changeOrder.status)) {
      activeChangeOrders += 1;
    }
    if (APPROVED_CHANGE_ORDER_STATUSES.has(changeOrder.status)) {
      approvedChangeOrders += 1;
    }
    if (REJECTED_CHANGE_ORDER_STATUSES.has(changeOrder.status)) {
      rejectedChangeOrders += 1;
    }

    proposedCostCents += getChangeOrderProposedCostCents(changeOrder);
    approvedCostCents += moneyToCents(changeOrder.approved_amount) ?? 0n;

    const impact = normalizeScheduleImpact(
      changeOrder.schedule_impact_days
    );
    const nextImpact = scheduleImpactDays + (impact ?? 0);
    if (impact !== undefined && Number.isSafeInteger(nextImpact)) {
      scheduleImpactDays = nextImpact;
    }
  }

  return {
    activeChangeOrders,
    approvedChangeOrders,
    rejectedChangeOrders,
    proposedCost: centsToDecimalString(proposedCostCents),
    approvedCost: centsToDecimalString(approvedCostCents),
    scheduleImpactDays,
  };
}

export function normalizeOptionalValue(value) {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

export function normalizeMoneyInput(value) {
  const normalized = String(value ?? "").trim();

  if (!normalized) return null;
  return MONEY_PATTERN.test(normalized) ? normalized : undefined;
}

export function normalizeScheduleImpact(value) {
  const normalized = String(value ?? "").trim();

  if (!normalized) return null;
  if (!WHOLE_NUMBER_PATTERN.test(normalized)) return undefined;

  const impact = Number(normalized);
  return Number.isSafeInteger(impact) ? impact : undefined;
}

export function formatCurrency(value) {
  const normalized = String(value ?? "").trim();
  const match = MONEY_PATTERN.exec(normalized);

  if (!match) return "Not specified";

  const [integerPart, decimalPart = ""] = normalized.split(".");
  const groupedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  return `$${groupedInteger}.${decimalPart.padEnd(2, "0")}`;
}

export function formatScheduleImpact(value) {
  const impact = normalizeScheduleImpact(value);
  if (impact === null || impact === undefined) return "Not specified";

  const prefix = impact > 0 ? "+" : "";
  return `${prefix}${impact} ${Math.abs(impact) === 1 ? "day" : "days"}`;
}

export function validateLifecycleDates({
  requestedDate,
  submittedDate,
  approvedDate,
  executedDate,
}) {
  const dates = [
    ["Requested", requestedDate],
    ["Submitted", submittedDate],
    ["Approved", approvedDate],
    ["Executed", executedDate],
  ];

  for (let index = 0; index < dates.length - 1; index += 1) {
    const [earlierLabel, earlierDate] = dates[index];
    const [laterLabel, laterDate] = dates[index + 1];

    if (earlierDate && laterDate && laterDate < earlierDate) {
      return `${laterLabel} date cannot be earlier than ${earlierLabel.toLowerCase()} date.`;
    }
  }

  return null;
}

export function validateChangeOrderForm({
  date,
  title,
  description,
  proposedAmount,
  approvedAmount,
  scheduleImpactDays,
  requestedDate,
  submittedDate,
  approvedDate,
  executedDate,
}) {
  if (!date) {
    return "Complete the record date before saving.";
  }

  if (!String(title ?? "").trim() && !String(description ?? "").trim()) {
    return "Enter a title or description before saving.";
  }

  if (normalizeMoneyInput(proposedAmount) === undefined) {
    return "Proposed amount must be a nonnegative value with no more than two decimal places.";
  }

  if (normalizeMoneyInput(approvedAmount) === undefined) {
    return "Approved amount must be a nonnegative value with no more than two decimal places.";
  }

  if (normalizeScheduleImpact(scheduleImpactDays) === undefined) {
    return "Schedule impact must be a whole number of days.";
  }

  return validateLifecycleDates({
    requestedDate,
    submittedDate,
    approvedDate,
    executedDate,
  });
}
