import {
  getCurrentWeekRange,
  parseLocalDateInputValue,
  toLocalDateInputValue,
} from "./date";

const INSPECTION_ISSUE_STATUSES = new Set(["Pending", "Fail", "Partial Pass"]);

function parseCurrencyAmount(value) {
  const amount = Number(String(value || "0").replace(/[$,\s]/g, ""));
  return Number.isFinite(amount) ? amount : 0;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function scheduledTasksOf(tasks) {
  return tasks.filter((task) => task.start_date && task.end_date);
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function getDashboardMetrics({
  tasks,
  tasksThisWeek,
  projectDelays,
  changeOrders,
}) {
  const pendingChangeOrders = changeOrders.filter(
    (changeOrder) => changeOrder.status === "Pending"
  );

  return {
    totalTasks: tasks.length,
    scheduledTasks: tasks.filter((task) => task.start_date && task.end_date)
      .length,
    tasksThisWeek: tasksThisWeek.length,
    recordedDelays: projectDelays.length,
    pendingChangeOrders: pendingChangeOrders.length,
    pendingChangeOrderValue: pendingChangeOrders.reduce(
      (total, changeOrder) => total + parseCurrencyAmount(changeOrder.amount),
      0
    ),
  };
}

export function getChangeOrderTotalsByCompany(changeOrders = []) {
  const totals = new Map();

  changeOrders.forEach((changeOrder) => {
    const company = changeOrder.company || "Unassigned";
    const amount = parseCurrencyAmount(changeOrder.amount);
    totals.set(company, (totals.get(company) || 0) + amount);
  });

  return Array.from(totals, ([company, total]) => ({ company, total }));
}

/** Time-based schedule position. There is no task-completion field, so this
 *  reports where "today" sits in the planned timeline plus counts of tasks
 *  that are active, past their planned finish, or still upcoming. */
export function getScheduleHealth(tasks = [], referenceDate = new Date()) {
  const scheduled = scheduledTasksOf(tasks);
  const today = toLocalDateInputValue(referenceDate);

  if (scheduled.length === 0) {
    return {
      hasSchedule: false,
      projectStart: null,
      projectEnd: null,
      timelineElapsedPct: 0,
      activeCount: 0,
      pastDueCount: 0,
      upcomingCount: 0,
      startingTodayCount: 0,
      nextTask: null,
    };
  }

  const projectStart = scheduled.reduce(
    (min, task) => (task.start_date < min ? task.start_date : min),
    scheduled[0].start_date
  );
  const projectEnd = scheduled.reduce(
    (max, task) => (task.end_date > max ? task.end_date : max),
    scheduled[0].end_date
  );

  const start = parseLocalDateInputValue(projectStart);
  const end = parseLocalDateInputValue(projectEnd);
  const now = parseLocalDateInputValue(today);

  let timelineElapsedPct = 0;
  if (start && end && now) {
    const totalMs = end - start;
    timelineElapsedPct =
      totalMs <= 0
        ? now >= start
          ? 100
          : 0
        : clampPercent(((now - start) / totalMs) * 100);
  }

  const upcoming = scheduled
    .filter((task) => task.start_date > today)
    .sort((left, right) => left.start_date.localeCompare(right.start_date));

  return {
    hasSchedule: true,
    projectStart,
    projectEnd,
    timelineElapsedPct,
    activeCount: scheduled.filter(
      (task) => task.start_date <= today && task.end_date >= today
    ).length,
    pastDueCount: scheduled.filter((task) => task.end_date < today).length,
    upcomingCount: upcoming.length,
    startingTodayCount: scheduled.filter((task) => task.start_date === today)
      .length,
    nextTask: upcoming[0] || null,
  };
}

export function getThisWeekProgress(tasks = [], referenceDate = new Date()) {
  const scheduled = scheduledTasksOf(tasks);
  const { start, end } = getCurrentWeekRange(referenceDate);
  const weekStart = toLocalDateInputValue(start);
  const weekEnd = toLocalDateInputValue(end);

  const inWeek = (value) => value >= weekStart && value <= weekEnd;

  return {
    starting: scheduled.filter((task) => inWeek(task.start_date)).length,
    finishing: scheduled.filter((task) => inWeek(task.end_date)).length,
    active: scheduled.filter(
      (task) => task.start_date <= weekEnd && task.end_date >= weekStart
    ).length,
  };
}

export function getUpcomingTasks(
  tasks = [],
  referenceDate = new Date(),
  { days = 14, limit = 5 } = {}
) {
  const today = toLocalDateInputValue(referenceDate);
  const horizon = toLocalDateInputValue(addDays(referenceDate, days));

  return scheduledTasksOf(tasks)
    .filter((task) => task.start_date > today && task.start_date <= horizon)
    .sort((left, right) => left.start_date.localeCompare(right.start_date))
    .slice(0, limit);
}

/** "Needs attention" list (not a formal CPM critical path): activities that are
 *  active today or already past their planned finish, most urgent first. */
export function getAttentionActivities(
  tasks = [],
  referenceDate = new Date(),
  { limit = 5 } = {}
) {
  const today = toLocalDateInputValue(referenceDate);
  const scheduled = scheduledTasksOf(tasks);

  const overdue = scheduled
    .filter((task) => task.end_date < today)
    .map((task) => ({ ...task, attention: "overdue" }))
    .sort((left, right) => left.end_date.localeCompare(right.end_date));

  const active = scheduled
    .filter((task) => task.start_date <= today && task.end_date >= today)
    .map((task) => ({ ...task, attention: "active" }))
    .sort((left, right) => left.end_date.localeCompare(right.end_date));

  return [...overdue, ...active].slice(0, limit);
}

export function getUpcomingInspections(
  inspections = [],
  referenceDate = new Date(),
  { limit = 5 } = {}
) {
  const today = toLocalDateInputValue(referenceDate);

  return inspections
    .filter(
      (inspection) =>
        inspection.date >= today || inspection.status === "Pending"
    )
    .sort((left, right) => String(left.date).localeCompare(String(right.date)))
    .slice(0, limit);
}

export function getTodaysFocus({
  tasks = [],
  inspections = [],
  notesDelays = [],
  changeOrders = [],
  referenceDate = new Date(),
} = {}) {
  const today = toLocalDateInputValue(referenceDate);

  const startingToday = scheduledTasksOf(tasks).filter(
    (task) => task.start_date === today
  );
  const inspectionsDueToday = inspections.filter(
    (inspection) => inspection.date === today
  );
  const activeDelays = notesDelays.filter(
    (entry) => entry.entry_type === "Delay"
  ).length;
  const pendingChangeOrders = changeOrders.filter(
    (changeOrder) => changeOrder.status === "Pending"
  ).length;

  const itemCount =
    startingToday.length +
    inspectionsDueToday.length +
    activeDelays +
    pendingChangeOrders;

  return {
    startingToday,
    startingTodayCount: startingToday.length,
    inspectionsDueToday,
    inspectionsDueTodayCount: inspectionsDueToday.length,
    activeDelays,
    pendingChangeOrders,
    itemCount,
    hasItems: itemCount > 0,
  };
}

/** Composite 0–100 heuristic. Weights are intentionally simple and tunable. */
export function getProjectHealthScore({
  activeDelays = 0,
  pendingChangeOrders = 0,
  inspectionIssues = 0,
  pastDueActivities = 0,
} = {}) {
  const score = clampPercent(
    100 -
      Math.min(activeDelays * 8, 30) -
      Math.min(pendingChangeOrders * 5, 20) -
      Math.min(inspectionIssues * 6, 18) -
      Math.min(pastDueActivities * 4, 20)
  );

  const band = score >= 80 ? "healthy" : score >= 60 ? "at-risk" : "critical";

  return { score, band };
}

export function getInspectionIssueCount(inspections = []) {
  return inspections.filter((inspection) =>
    INSPECTION_ISSUE_STATUSES.has(inspection.status)
  ).length;
}

/** Merge dated records into one reverse-chronological feed, flagging anything
 *  from yesterday or later as new ("what changed since yesterday"). */
export function getRecentActivity(
  { dailyLogs = [], inspections = [], changeOrders = [], notesDelays = [] } = {},
  referenceDate = new Date(),
  { limit = 8 } = {}
) {
  const sinceKey = toLocalDateInputValue(addDays(referenceDate, -1));

  const items = [
    ...dailyLogs.map((log) => ({
      key: `log-${log.id}`,
      date: log.date,
      type: "log",
      label: `Daily log — ${log.company || "Unassigned"} (${
        log.manpower || 0
      } crew)`,
    })),
    ...inspections.map((inspection) => ({
      key: `inspection-${inspection.id}`,
      date: inspection.date,
      type: "inspection",
      label: `Inspection — ${inspection.inspection_type}: ${inspection.status}`,
    })),
    ...changeOrders.map((changeOrder) => ({
      key: `co-${changeOrder.id}`,
      date: changeOrder.date,
      type: "changeOrder",
      label: `${changeOrder.co_number} ${changeOrder.status} — ${
        changeOrder.company || "Unassigned"
      }`,
    })),
    ...notesDelays.map((entry) => ({
      key: `nd-${entry.id}`,
      date: entry.date,
      type: entry.entry_type === "Delay" ? "delay" : "note",
      label: `${entry.entry_type} — ${entry.company || entry.description}`,
    })),
  ];

  return items
    .filter((item) => item.date)
    .map((item) => ({ ...item, isNew: item.date >= sinceKey }))
    .sort((left, right) => String(right.date).localeCompare(String(left.date)))
    .slice(0, limit);
}
