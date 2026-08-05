import EmptyState from "./EmptyState";
import {
  formatDisplayDate as formatDate,
  parseLocalDateInputValue,
} from "../utils/date";
import { getTaskDepthFromList } from "../utils/taskHierarchy";
import { buildWbsMap, getTaskDependencies } from "../utils/taskReferences";
import { formatProgressStatus } from "../utils/scheduleProgress";

const MS_PER_DAY = 1000 * 60 * 60 * 24;
const DAY_WIDTH = 34;
const ROW_HEIGHT = 38;

function parseDate(value) {
  return parseLocalDateInputValue(value);
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
  { swatch: "in-progress", label: "In Progress" },
  { swatch: "completed", label: "Completed" },
  { swatch: "milestone", label: "Milestone" },
  { swatch: "constraint", label: "Constraint" },
  { swatch: "dependency", label: "Dependency" },
  { swatch: "data-date", label: "Data Date" },
  { swatch: "today", label: "Today" },
];

function GanttChart({ tasks, selectedTaskId, dataDate }) {
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
  const parsedDataDate = parseDate(dataDate);
  const startValues = scheduledTasks.map((task) =>
    parseDate(task.start_date).getTime()
  );
  const endValues = scheduledTasks.map((task) =>
    parseDate(task.end_date).getTime()
  );
  scheduledTasks.forEach((task) => {
    const constraintDate = parseDate(task.constraint_date);
    if (constraintDate) {
      startValues.push(constraintDate.getTime());
      endValues.push(constraintDate.getTime());
    }
  });
  if (parsedDataDate) {
    startValues.push(parsedDataDate.getTime());
    endValues.push(parsedDataDate.getTime());
  }
  const projectStartMs = Math.min(...startValues);
  const projectEndMs = Math.max(...endValues);

  const projectStartDate = new Date(projectStartMs);
  projectStartDate.setHours(0, 0, 0, 0);

  const totalDays = Math.ceil((projectEndMs - projectStartMs) / MS_PER_DAY) + 1;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIndex = Math.round(
    (today.getTime() - projectStartDate.getTime()) / MS_PER_DAY
  );
  const todayVisible = todayIndex >= 0 && todayIndex < totalDays;
  const dataDateIndex = parsedDataDate
    ? Math.round(
        (parsedDataDate.getTime() - projectStartDate.getTime()) / MS_PER_DAY
      )
    : -1;
  const dataDateVisible = dataDateIndex >= 0 && dataDateIndex < totalDays;

  const isDependent = (task, selectedId) => {
    if (!selectedId) return false;
    const pending = [task];
    const visited = new Set();
    while (pending.length) {
      const current = pending.pop();
      for (const dependency of getTaskDependencies(current)) {
        if (dependency.predecessor_task_id === selectedId) return true;
        if (visited.has(dependency.predecessor_task_id)) continue;
        visited.add(dependency.predecessor_task_id);
        const predecessor = taskMap.get(dependency.predecessor_task_id);
        if (predecessor) pending.push(predecessor);
      }
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
  const timelineWidth = totalDays * DAY_WIDTH;
  const bodyHeight = visibleTasks.length * ROW_HEIGHT;
  const visibleRowById = new Map(
    visibleTasks.map((task, index) => [task.id, index])
  );
  const dateOffset = (value) =>
    Math.round((parseDate(value).getTime() - projectStartMs) / MS_PER_DAY);
  const taskAnchor = (task, point) =>
    point === "start"
      ? dateOffset(task.start_date) * DAY_WIDTH + 2
      : (dateOffset(task.end_date) + 1) * DAY_WIDTH - 2;
  const dependencyLines = visibleTasks.flatMap((task) => {
    const successorRow = visibleRowById.get(task.id);
    return getTaskDependencies(task).flatMap((dependency) => {
      const predecessor = taskMap.get(dependency.predecessor_task_id);
      const predecessorRow = visibleRowById.get(dependency.predecessor_task_id);
      if (!predecessor || predecessorRow == null) return [];
      const type = dependency.dependency_type || "FS";
      const x1 = taskAnchor(
        predecessor,
        type[0] === "S" ? "start" : "finish"
      );
      const x2 = taskAnchor(task, type[1] === "S" ? "start" : "finish");
      const y1 = predecessorRow * ROW_HEIGHT + ROW_HEIGHT / 2;
      const y2 = successorRow * ROW_HEIGHT + ROW_HEIGHT / 2;
      const direction = x2 >= x1 ? 1 : -1;
      const elbowX = x1 + direction * Math.max(10, Math.abs(x2 - x1) / 2);
      const lag = Number(dependency.lag_days) || 0;
      return [
        {
          key: `${task.id}:${predecessor.id}`,
          type,
          lag,
          label: `${wbsMap.get(predecessor.id)} ${type}${
            lag ? ` ${lag > 0 ? "+" : ""}${lag} days` : ""
          } to ${wbsMap.get(task.id)}`,
          path: `M ${x1} ${y1} L ${elbowX} ${y1} L ${elbowX} ${y2} L ${x2} ${y2}`,
          labelX: elbowX + 3,
          labelY: (y1 + y2) / 2 - 3,
        },
      ];
    });
  });

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
                  {task.is_milestone && (
                    <>
                      <span
                        className="gantt-table__milestone"
                        aria-hidden="true"
                      />
                      <span className="visually-hidden"> Milestone</span>
                    </>
                  )}
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
                const isDataDate = dataDateVisible && index === dataDateIndex;

                const classes = [
                  "gantt-day",
                  isWeekend ? "gantt-day--weekend" : "",
                  isToday ? "gantt-day--today" : "",
                  isDataDate ? "gantt-day--data-date" : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                return (
                  <div
                    key={index}
                    className={classes}
                    style={{ width: DAY_WIDTH }}
                    title={
                      isDataDate ? "Data Date" : isToday ? "Today" : undefined
                    }
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
              style={{
                backgroundImage: timelineBackground,
                height: bodyHeight,
              }}
            >
              {dependencyLines.length > 0 && (
                <svg
                  className="gantt-dependencies"
                  width={timelineWidth}
                  height={bodyHeight}
                  viewBox={`0 0 ${timelineWidth} ${bodyHeight}`}
                  role="img"
                  aria-label="Schedule dependencies"
                >
                  <defs>
                    <marker
                      id="gantt-dependency-arrow"
                      markerWidth="6"
                      markerHeight="6"
                      refX="5"
                      refY="3"
                      orient="auto"
                    >
                      <path d="M0,0 L6,3 L0,6 Z" />
                    </marker>
                  </defs>
                  {dependencyLines.map((line) => (
                    <g
                      key={line.key}
                      className={`gantt-dependency gantt-dependency--${line.type.toLowerCase()}`}
                    >
                      <title>{line.label}</title>
                      <path
                        d={line.path}
                        markerEnd="url(#gantt-dependency-arrow)"
                      />
                      <text x={line.labelX} y={line.labelY}>
                        {line.type}
                        {line.lag
                          ? `${line.lag > 0 ? "+" : ""}${line.lag}`
                          : ""}
                      </text>
                    </g>
                  ))}
                </svg>
              )}
              {dataDateVisible && (
                <div
                  className="gantt-data-date-line"
                  style={{ left: dataDateIndex * DAY_WIDTH + DAY_WIDTH / 2 }}
                  aria-label={`Data Date ${formatDate(dataDate)}`}
                >
                  <span>Data Date</span>
                </div>
              )}
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
                const progressStatus = task.progress_status || "not_started";
                const isMilestone = Boolean(task.is_milestone);
                const constraintDate = parseDate(task.constraint_date);
                const constraintOffset = constraintDate
                  ? Math.round(
                      (constraintDate.getTime() - projectStartMs) / MS_PER_DAY
                    )
                  : null;

                const barClasses = [
                  "gantt-bar",
                  isMilestone ? "gantt-bar--milestone" : "",
                  isSummary ? "gantt-bar--summary" : "",
                  isSelected ? "gantt-bar--selected" : "",
                  !isSelected && isCritical ? "gantt-bar--critical" : "",
                  !isSelected && !isCritical && dependent
                    ? "gantt-bar--dependent"
                    : "",
                  !isSummary && progressStatus === "in_progress"
                    ? "gantt-bar--in-progress"
                    : "",
                  !isSummary && progressStatus === "completed"
                    ? "gantt-bar--completed"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                const label = `${task.name}${
                  isSummary ? " summary" : ""
                }, ${formatDate(task.start_date)} through ${formatDate(
                  task.end_date
                )}, ${formatProgressStatus(progressStatus)}, ${
                  task.percent_complete || 0
                } percent complete${
                  isMilestone ? ", milestone" : ""
                }${
                  task.constraint_type && task.constraint_type !== "ASAP"
                    ? `, ${task.constraint_type} constraint ${formatDate(
                        task.constraint_date
                      )}${task.constraint_violated ? " violated" : ""}`
                    : ""
                }${
                  task.out_of_sequence ? ", out of sequence" : ""
                }${isCritical ? ", on the critical path" : ""}${
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
                        left: isMilestone
                          ? offsetDays * DAY_WIDTH + DAY_WIDTH / 2 - 7
                          : offsetDays * DAY_WIDTH + 1,
                        width: isMilestone
                          ? 14
                          : durationDays * DAY_WIDTH - 2,
                      }}
                    />
                    {constraintOffset != null && (
                      <div
                        className={`gantt-constraint-marker${
                          task.constraint_violated
                            ? " gantt-constraint-marker--violated"
                            : ""
                        }`}
                        style={{
                          left:
                            constraintOffset * DAY_WIDTH + DAY_WIDTH / 2 - 5,
                        }}
                        role="img"
                        aria-label={`${task.constraint_type} constraint for ${
                          task.name
                        } on ${formatDate(task.constraint_date)}${
                          task.constraint_violated ? ", violated" : ""
                        }`}
                        title={`${task.constraint_type} ${formatDate(
                          task.constraint_date
                        )}`}
                      />
                    )}
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
