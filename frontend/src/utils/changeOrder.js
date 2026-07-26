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
const WHOLE_NUMBER_PATTERN = /^-?\d+$/;

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
  const normalized = String(value ?? "").trim();

  if (!WHOLE_NUMBER_PATTERN.test(normalized)) return "Not specified";

  const impact = Number(normalized);
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
