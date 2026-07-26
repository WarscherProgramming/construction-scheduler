/** ISO "YYYY-MM-DD" → display "MM/DD/YYYY"; falsy → "-".
 *  Already-formatted values pass through unchanged. */
export function formatDisplayDate(value) {
  if (!value) return "-";

  const normalized = String(value);
  if (normalized.includes("/")) return normalized;

  const [y, m, d] = normalized.split("-");
  return `${m}/${d}/${y}`;
}

export function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function toLocalDateInputValue(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export function parseLocalDateInputValue(value) {
  if (!value) return null;

  const [year, month, day] = String(value).split("-").map(Number);
  if (!year || !month || !day) return null;

  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function isPastLocalDate(value, today = new Date()) {
  return Boolean(value) && value < toLocalDateInputValue(today);
}

export function getCurrentWeekRange(date = new Date()) {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - start.getDay());

  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  end.setHours(23, 59, 59, 999);

  return { start, end };
}

export function sortByDateDescending(records) {
  return [...records].sort((left, right) => {
    const dateComparison = String(right.date || "").localeCompare(
      String(left.date || "")
    );

    if (dateComparison !== 0) return dateComparison;
    return Number(right.id || 0) - Number(left.id || 0);
  });
}
