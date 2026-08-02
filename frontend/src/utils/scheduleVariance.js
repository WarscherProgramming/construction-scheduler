import { formatDisplayDate, parseLocalDateInputValue } from "./date";


export function formatScheduleDate(value) {
  return parseLocalDateInputValue(value)
    ? formatDisplayDate(value)
    : "Unavailable";
}


export function formatScheduleTimestamp(value) {
  if (
    !value ||
    !/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/i.test(String(value))
  ) {
    return "Unavailable";
  }
  const parsed = new Date(value);

  if (!value || Number.isNaN(parsed.getTime())) return "Unavailable";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}


export function formatWorkdayVariance(value) {
  if (!Number.isInteger(value)) return "Unavailable";
  if (value === 0) return "No variance";

  const count = Math.abs(value);
  return `${count} workday${count === 1 ? "" : "s"} ${
    value > 0 ? "later" : "earlier"
  }`;
}


export function formatDurationVariance(value) {
  if (!Number.isInteger(value)) return "Unavailable";
  if (value === 0) return "No change";

  const count = Math.abs(value);
  return `${count} day${count === 1 ? "" : "s"} ${
    value > 0 ? "longer" : "shorter"
  }`;
}


export function formatCriticalChange(value) {
  const labels = {
    newly_critical: "Newly critical",
    no_longer_critical: "No longer critical",
    remained_critical: "Remained critical",
    remained_noncritical: "Remained noncritical",
  };

  return labels[value] || "Not comparable";
}


export function formatComparisonStatus(value) {
  const labels = {
    slipped: "Slipped",
    improved: "Improved",
    unchanged: "Unchanged",
    added: "Added",
    removed: "Removed",
    unscheduled: "Unscheduled",
    incomparable: "Incomparable",
  };

  return labels[value] || "Unknown";
}


export function getStructuralChanges(task) {
  const labels = [];

  if (task.hierarchy_changed) labels.push("Hierarchy changed");
  if (task.dependency_changed) labels.push("Dependency changed");
  if (task.duration_changed) labels.push("Duration changed");
  if (task.manual_start_changed) labels.push("Manual start changed");
  if (task.order_changed) labels.push("Order changed");

  return labels;
}
