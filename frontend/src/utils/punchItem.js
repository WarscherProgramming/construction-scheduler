import { isPastLocalDate } from "./date";

const OVERDUE_STATUSES = new Set(["Open", "In Progress"]);

export function isPunchItemOverdue(punchItem, today = new Date()) {
  return (
    OVERDUE_STATUSES.has(punchItem.status) &&
    isPastLocalDate(punchItem.due_date, today)
  );
}
