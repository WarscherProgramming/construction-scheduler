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
  const date = parseLocalDateInputValue(value);
  return date ? DATE_FORMATTER.format(date) : "Date unavailable";
}
