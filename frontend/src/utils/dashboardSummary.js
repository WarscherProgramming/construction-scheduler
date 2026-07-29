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


export function formatDashboardCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }

  const amount = Number(value);
  return Number.isFinite(amount)
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
  if (!Number.isFinite(duration)) return null;

  return `${duration} ${duration === 1 ? "day" : "days"}`;
}
