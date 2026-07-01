import EmptyState from "./EmptyState";
import { getTaskDepthFromList } from "../utils/taskHierarchy";
import { buildWbsMap } from "../utils/taskReferences";

const MS_PER_DAY = 1000 * 60 * 60 * 24;
const DAY_WIDTH = 34;
const ROW_HEIGHT = 38;

function parseDate(value) {
  if (!value) return null;

  if (value.includes("/")) {
    const [m, d, y] = value.split("/").map(Number);
    return new Date(y, m - 1, d);
  }

  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatDate(value) {
  if (!value) return "-";

  return parseDate(value).toLocaleDateString("en-US", {
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
  });
}

/**
 * Weekend shading and day grid lines as repeating gradients on the row
 * area — one background instead of a rows × days grid of divs.
 */
function buildTimelineBackground(startDow) {
  const weekendStops = [];

  for (let offset = 0; offset < 7; offset += 1) {
    const day = (startDow + offset) % 7;
    const color =
      day === 0 || day === 6 ? "rgba(226, 232, 240, 0.55)" : "transparent";
    weekendStops.push(
      `${color} ${offset * DAY_WIDTH}px ${(offset + 1) * DAY_WIDTH}px`
    );
  }

  const weekendLayer = `repeating-linear-gradient(to right, ${weekendStops.join(
    ", "
  )})`;
  const gridLayer = `repeating-linear-gradient(to right, transparent 0 ${
    DAY_WIDTH - 1
  }px, rgba(15, 23, 42, 0.06) ${DAY_WIDTH - 1}px ${DAY_WIDTH}px)`;

  return `${gridLayer}, ${weekendLayer}`;
}

const LEGEND = [
  { swatch: "task", label: "Task" },
  { swatch: "summary", label: "Summary" },
  { swatch: "critical", label: "Critical path" },
  { swatch: "selected", label: "Selected" },
  { swatch: "dependent", label: "Depends on selection" },
  { swatch: "today", label: "Today" },
];

function GanttChart({ tasks, selectedTaskId }) {
  if (!tasks.length) {
    return (
      <EmptyState
        title="No tasks yet"
        description="Add schedule tasks to see them on the Gantt chart."
      />
    );
  }

  const taskMap = new Map(tasks.map((task) => [task.id, task]));
  const parentIds = new Set(
    tasks
      .map((task) => task.parent_task_id)
      .filter((parentId) => parentId !== null && parentId !== undefined)
  );

  const isHiddenByCollapse = (task) => {
    let parentId = task.parent_task_id;
    const visited = new Set();

    while (parentId && !visited.has(parentId)) {
      visited.add(parentId);
      const parent = taskMap.get(parentId);
      if (!parent) break;
      if (parent.is_collapsed) return true;
      parentId = parent.parent_task_id;
    }

    return false;
  };

  const scheduledTasks = tasks.filter(
    (task) => task.start_date && task.end_date
  );
  const visibleTasks = scheduledTasks.filter(
    (task) => !isHiddenByCollapse(task)
  );

  if (!visibleTasks.length) {
    return (
      <EmptyState
        title="No scheduled tasks yet"
        description="Tasks appear on the Gantt once they have start and end dates."
      />
    );
  }

  // Time range covers every scheduled task (collapsing rows never rescales
  // the timeline).
  const projectStartMs = Math.min(
    ...scheduledTasks.map((task) => parseDate(task.start_date).getTime())
  );
  const projectEndMs = Math.max(
    ...scheduledTasks.map((task) => parseDate(task.end_date).getTime())
  );

  const projectStartDate = new Date(projectStartMs);
  projectStartDate.setHours(0, 0, 0, 0);

  const totalDays = Math.ceil((projectEndMs - projectStartMs) / MS_PER_DAY) + 1;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIndex = Math.round(
    (today.getTime() - projectStartDate.getTime()) / MS_PER_DAY
  );
  const todayVisible = todayIndex >= 0 && todayIndex < totalDays;

  const isDependent = (task, selectedId) => {
    if (!selectedId) return false;

    let current = task;
    const visited = new Set();

    while (
      current.predecessor_task_id &&
      !visited.has(current.predecessor_task_id)
    ) {
      visited.add(current.predecessor_task_id);
      const predecessorTask = taskMap.get(current.predecessor_task_id);

      if (!predecessorTask) break;
      if (predecessorTask.id === selectedId) return true;

      current = predecessorTask;
    }

    return false;
  };

  const months = [];
  let currentMonth = null;
  let count = 0;

  for (let i = 0; i < totalDays; i += 1) {
    const date = new Date(projectStartDate);
    date.setDate(date.getDate() + i);

    const month = date.toLocaleString("default", {
      month: "short",
      year: "2-digit",
    });

    if (month !== currentMonth) {
      if (currentMonth !== null) {
        months.push({ name: currentMonth, days: count });
      }
      currentMonth = month;
      count = 1;
    } else {
      count += 1;
    }
  }

  months.push({ name: currentMonth, days: count });

  const timelineBackground = buildTimelineBackground(projectStartDate.getDay());
  const wbsMap = buildWbsMap(tasks);

  return (
    <div className="gantt">
      <ul className="gantt-legend">
        {LEGEND.map((entry) => (
          <li key={entry.swatch} className="gantt-legend__item">
            <span
              className={`gantt-legend__swatch gantt-legend__swatch--${entry.swatch}`}
              aria-hidden="true"
            />
            {entry.label}
          </li>
        ))}
      </ul>

      <div className="gantt-frame">
        {/* Left task table */}
        <div className="gantt-table">
          <div
            className="gantt-table__header"
            style={{ height: 56 }}
          >
            <div className="gantt-table__cell">WBS</div>
            <div className="gantt-table__cell">Task</div>
            <div className="gantt-table__cell">Dur</div>
            <div className="gantt-table__cell">Start</div>
            <div className="gantt-table__cell">End</div>
          </div>

          {visibleTasks.map((task) => {
            const isSelected = task.id === selectedTaskId;
            const dependent = isDependent(task, selectedTaskId);
            const isSummary = parentIds.has(task.id);
            const depth = getTaskDepthFromList(tasks, task);

            const rowClasses = [
              "gantt-table__row",
              isSummary ? "gantt-table__row--summary" : "",
              isSelected ? "gantt-table__row--selected" : "",
              !isSelected && dependent ? "gantt-table__row--dependent" : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <div
                key={task.id}
                className={rowClasses}
                style={{ height: ROW_HEIGHT }}
              >
                {(isSelected || dependent) && (
                  <span className="visually-hidden">
                    {isSelected
                      ? "Selected task."
                      : "Depends on the selected task."}
                  </span>
                )}
                <div className="gantt-table__cell gantt-table__cell--wbs">
                  {wbsMap.get(task.id)}
                </div>
                <div
                  className="gantt-table__cell gantt-table__cell--name"
                  style={{ paddingLeft: 10 + depth * 16 }}
                  title={task.name}
                >
                  {task.name}
                </div>
                <div className="gantt-table__cell">{task.duration}</div>
                <div className="gantt-table__cell gantt-table__cell--date">
                  {formatDate(task.start_date)}
                </div>
                <div className="gantt-table__cell gantt-table__cell--date">
                  {formatDate(task.end_date)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Timeline */}
        <div className="gantt-timeline">
          <div style={{ width: totalDays * DAY_WIDTH, minWidth: "100%" }}>
            <div className="gantt-months">
              {months.map((month, index) => (
                <div
                  key={index}
                  className="gantt-month"
                  style={{ width: month.days * DAY_WIDTH }}
                >
                  {month.name}
                </div>
              ))}
            </div>

            <div className="gantt-days">
              {Array.from({ length: totalDays }).map((_, index) => {
                const date = new Date(projectStartDate);
                date.setDate(date.getDate() + index);

                const isWeekend = date.getDay() === 0 || date.getDay() === 6;
                const isToday = todayVisible && index === todayIndex;

                const classes = [
                  "gantt-day",
                  isWeekend ? "gantt-day--weekend" : "",
                  isToday ? "gantt-day--today" : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                return (
                  <div
                    key={index}
                    className={classes}
                    style={{ width: DAY_WIDTH }}
                    title={isToday ? "Today" : undefined}
                  >
                    <div>
                      {date.toLocaleDateString("en-US", { weekday: "narrow" })}
                    </div>
                    <div>{date.getDate()}</div>
                  </div>
                );
              })}
            </div>

            <div
              className="gantt-body"
              style={{ backgroundImage: timelineBackground }}
            >
              {todayVisible && (
                <div
                  className="gantt-today-column"
                  style={{
                    left: todayIndex * DAY_WIDTH,
                    width: DAY_WIDTH,
                  }}
                  aria-hidden="true"
                />
              )}

              {visibleTasks.map((task) => {
                const startMs = parseDate(task.start_date).getTime();
                const endMs = parseDate(task.end_date).getTime();

                const offsetDays = Math.round(
                  (startMs - projectStartMs) / MS_PER_DAY
                );
                const durationDays =
                  Math.round((endMs - startMs) / MS_PER_DAY) + 1;

                const isSelected = task.id === selectedTaskId;
                const dependent = isDependent(task, selectedTaskId);
                const isSummary = parentIds.has(task.id);
                const isCritical = Boolean(task.is_critical);

                const barClasses = [
                  "gantt-bar",
                  isSummary ? "gantt-bar--summary" : "",
                  isSelected ? "gantt-bar--selected" : "",
                  !isSelected && isCritical ? "gantt-bar--critical" : "",
                  !isSelected && !isCritical && dependent
                    ? "gantt-bar--dependent"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                const label = `${task.name}${
                  isSummary ? " summary" : ""
                }, ${formatDate(task.start_date)} through ${formatDate(
                  task.end_date
                )}${isCritical ? ", on the critical path" : ""}${
                  isSelected
                    ? ", selected"
                    : dependent
                      ? ", depends on selected task"
                      : ""
                }`;

                return (
                  <div
                    key={task.id}
                    className="gantt-row"
                    style={{ height: ROW_HEIGHT }}
                    role="img"
                    aria-label={label}
                  >
                    <div
                      className={barClasses}
                      style={{
                        left: offsetDays * DAY_WIDTH + 1,
                        width: durationDays * DAY_WIDTH - 2,
                      }}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GanttChart;
