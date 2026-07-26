import { isPastLocalDate } from "./date";

const RESOLVED_STATUSES = new Set([
  "Approved",
  "Revise and Resubmit",
  "Rejected",
]);

export function isSubmittalOverdue(submittal, today = new Date()) {
  return (
    !RESOLVED_STATUSES.has(submittal.status) &&
    isPastLocalDate(submittal.required_by_date, today)
  );
}
