import { parseLocalDateInputValue } from "./date";


const CURRENCY_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

const TIMESTAMP_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});


export function formatDashboardCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }

  const amount = Number(value);
  return Number.isFinite(amount) && amount >= 0
    ? CURRENCY_FORMATTER.format(amount)
    : "Unavailable";
}


export function formatDashboardDate(value) {
  return formatOptionalDashboardDate(value) || "Date unavailable";
}


export function formatOptionalDashboardDate(value) {
  const date = parseLocalDateInputValue(value);
  return date ? DATE_FORMATTER.format(date) : null;
}


export function formatDashboardDuration(value) {
  if (value === null || value === undefined || value === "") return null;

  const duration = Number(value);
  if (!Number.isInteger(duration) || duration < 0) return null;

  return `${duration} ${duration === 1 ? "day" : "days"}`;
}


export function formatDashboardTimestamp(value) {
  if (
    !value ||
    !/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/i.test(String(value))
  ) {
    return null;
  }

  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return null;

  return TIMESTAMP_FORMATTER.format(timestamp);
}


export function formatDashboardCount(value) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }

  const count = Number(value);
  return Number.isInteger(count) && count >= 0
    ? count
    : "Unavailable";
}


export function calculateDistributionValue(count, total) {
  const numericCount = Number(count);
  const numericTotal = Number(total);

  if (
    !Number.isInteger(numericCount) ||
    !Number.isInteger(numericTotal) ||
    numericCount <= 0 ||
    numericTotal <= 0
  ) {
    return 0;
  }

  return Math.min(100, (numericCount / numericTotal) * 100);
}


export function formatDashboardLinkContext(value, fallback) {
  const normalized =
    typeof value === "string" ? value.trim() : "";
  const context = normalized || fallback;

  if (context.length <= 64) return context;
  return `${context.slice(0, 61).trimEnd()}...`;
}
