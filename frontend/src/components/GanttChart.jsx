
function GanttChart({ tasks, selectedTaskId }) {
  if (!tasks.length) return <p>No tasks yet</p>;

  const MS_PER_DAY = 1000 * 60 * 60 * 24;

  const parseDate = (date) => {
    if (!date) return null;

    if (date.includes("/")) {
      const [m, d, y] = date.split("/").map(Number);
      return new Date(y, m - 1, d);
    }

    const [y, m, d] = date.split("-").map(Number);
    return new Date(y, m - 1, d);
  };

  const formatDate = (date) => {
    if (!date) return "-";

    const parsed = parseDate(date);

    return parsed.toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  const scheduledTasks = tasks
    .filter((task) => task.start_date && task.end_date)
    .filter((task) => task.parent_task_id === null);
    
  if (!scheduledTasks.length) {
    return <p>No scheduled tasks yet</p>;
  }

  const taskStartTimes = scheduledTasks.map((task) =>
    parseDate(task.start_date).getTime()
  );

  const taskEndTimes = scheduledTasks.map((task) =>
    parseDate(task.end_date).getTime()
  );

  const projectStartMs = Math.min(...taskStartTimes);
  const projectEndMs = Math.max(...taskEndTimes);

  const projectStartDate = new Date(projectStartMs);
  projectStartDate.setHours(0, 0, 0, 0);

  const totalDays =
    Math.ceil((projectEndMs - projectStartMs) / MS_PER_DAY) + 1;

  const dayWidth = 34;
  const rowHeight = 42;
  const timelineHeaderHeight = 64;
  const barHeight = 18;

  const isDependent = (task, selectedId) => {
    if (!selectedId) return false;

    let current = task;
    const visited = new Set();
    const taskMap = new Map(tasks.map((candidate) => [candidate.id, candidate]));

    while (
      current.predecessor_task_id &&
      !visited.has(current.predecessor_task_id)
    ) {
      visited.add(current.predecessor_task_id);
      const predecessorTask = taskMap.get(current.predecessor_task_id);

      if (!predecessorTask) break;

      if (predecessorTask.id === selectedId) {
        return true;
      }

      current = predecessorTask;
    }

    return false;
  };

  const months = [];
  let currentMonth = null;
  let count = 0;

  for (let i = 0; i < totalDays; i++) {
    const date = new Date(projectStartDate);
    date.setDate(date.getDate() + i);

    const month = date.toLocaleString("default", {
      month: "short",
      year: "2-digit",
    });

    if (month !== currentMonth) {
      if (currentMonth !== null) {
        months.push({
          name: currentMonth,
          days: count,
        });
      }

      currentMonth = month;
      count = 1;
    } else {
      count++;
    }
  }

  months.push({
    name: currentMonth,
    days: count,
  });

  return (
    <div style={{ marginTop: "20px" }}>

      <div
        className="gantt-frame"
        style={{
          display: "flex",
          border: "1px solid #ddd",
          overflow: "hidden",
          width: "100%",
        }}
      >
        {/* LEFT TASK TABLE */}
        <div
          style={{
            width: "500px",
            minWidth: "500px",
            borderRight: "1px solid #ddd",
            background: "#fff",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 70px 110px 110px",
              height: timelineHeaderHeight,
              alignItems: "center",
              fontWeight: "bold",
              background: "#f3f4f6",
              borderBottom: "1px solid #ddd",
              fontSize: "13px",
            }}
          >
            <div style={{ padding: "8px", borderRight: "1px solid #ddd" }}>
              Task Name
            </div>
            <div style={{ padding: "8px", borderRight: "1px solid #ddd" }}>
              Dur
            </div>
            <div style={{ padding: "8px", borderRight: "1px solid #ddd" }}>
              Start
            </div>
            <div style={{ padding: "8px" }}>End</div>
          </div>

          {scheduledTasks.map((task, index) => {
            const isSelected = task.id === selectedTaskId;
            const dependent = isDependent(task, selectedTaskId);

            return (
              <div
                key={task.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 70px 110px 110px",
                  height: rowHeight,
                  alignItems: "center",
                  borderBottom: "1px solid #eee",
                  fontSize: "13px",
                  background: isSelected
                    ? "#e0f2fe"
                    : dependent
                    ? "#ecfdf5"
                    : index % 2 === 0
                    ? "#ffffff"
                    : "#f9fafb",
                }}
              >
                {(isSelected || dependent) && (
                  <span className="visually-hidden">
                    {isSelected
                      ? "Selected task."
                      : "Depends on the selected task."}
                  </span>
                )}
                <div
                  style={{
                    padding: "8px",
                    borderRight: "1px solid #eee",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    fontWeight: task.predecessor_task_id ? "normal" : "bold",
                  }}
                  title={task.name}
                >
                  {task.name}
                </div>

                <div
                  style={{
                    padding: "8px",
                    borderRight: "1px solid #eee",
                  }}
                >
                  {task.duration}
                </div>

                <div
                  style={{
                    padding: "8px",
                    borderRight: "1px solid #eee",
                  }}
                >
                  {formatDate(task.start_date)}
                </div>

                <div style={{ padding: "8px" }}>
                  {formatDate(task.end_date)}
                </div>
              </div>
            );
          })}
        </div>

        {/* RIGHT TIMELINE */}
        <div
          style={{
            flex: 1,
            overflowX: "auto",
            position: "relative",
          }}
        >
          <div
            style={{
              width: totalDays * dayWidth,
              minWidth: "100%",
            }}
          >
            {/* MONTH HEADER */}
            <div style={{ display: "flex", height: "32px" }}>
              {months.map((month, index) => (
                <div
                  key={index}
                  style={{
                    width: month.days * dayWidth,
                    textAlign: "center",
                    fontWeight: "bold",
                    fontSize: "13px",
                    background: "#dbeafe",
                    borderRight: "1px solid #ccc",
                    borderBottom: "1px solid #ccc",
                    boxSizing: "border-box",
                    paddingTop: "7px",
                  }}
                >
                  {month.name}
                </div>
              ))}
            </div>

            {/* DAY HEADER */}
            <div style={{ display: "flex", height: "32px" }}>
              {Array.from({ length: totalDays }).map((_, index) => {
                const date = new Date(projectStartDate);
                date.setDate(date.getDate() + index);

                const isWeekend =
                  date.getDay() === 0 || date.getDay() === 6;

                return (
                  <div
                    key={index}
                    style={{
                      width: dayWidth,
                      textAlign: "center",
                      fontSize: "11px",
                      background: isWeekend ? "#e5e7eb" : "#f3f4f6",
                      borderRight: "1px solid #ddd",
                      borderBottom: "1px solid #ccc",
                      boxSizing: "border-box",
                      paddingTop: "4px",
                    }}
                  >
                    <div>
                      {date.toLocaleDateString("en-US", {
                        weekday: "narrow",
                      })}
                    </div>
                    <div>{date.getDate()}</div>
                  </div>
                );
              })}
            </div>

            {/* TASK ROWS */}
            {scheduledTasks.map((task, rowIndex) => {
              const startMs = parseDate(task.start_date).getTime();
              const endMs = parseDate(task.end_date).getTime();

              const offsetDays = Math.round(
                (startMs - projectStartMs) / MS_PER_DAY
              );

              const durationDays =
                Math.round((endMs - startMs) / MS_PER_DAY) + 1;

              const isSelected = task.id === selectedTaskId;
              const dependent = isDependent(task, selectedTaskId);

              return (
                <div
                  key={task.id}
                  style={{
                    height: rowHeight,
                    position: "relative",
                    borderBottom: "1px solid #eee",
                    background:
                      rowIndex % 2 === 0 ? "#ffffff" : "#f9fafb",
                  }}
                >
                  {/* DAY GRID */}
                  <div
                    role="img"
                    aria-label={`${task.name}, ${formatDate(
                      task.start_date
                    )} through ${formatDate(task.end_date)}${
                      isSelected
                        ? ", selected"
                        : dependent
                          ? ", depends on selected task"
                          : ""
                    }`}
                    style={{
                      display: "flex",
                      height: "100%",
                      position: "absolute",
                      inset: 0,
                    }}
                  >
                    {Array.from({ length: totalDays }).map((_, dayIndex) => {
                      const date = new Date(projectStartDate);
                      date.setDate(date.getDate() + dayIndex);

                      const isWeekend =
                        date.getDay() === 0 || date.getDay() === 6;

                      return (
                        <div
                          key={dayIndex}
                          style={{
                            width: dayWidth,
                            height: "100%",
                            background: isWeekend
                              ? "rgba(229, 231, 235, 0.7)"
                              : "transparent",
                            borderRight: "1px solid #eee",
                            boxSizing: "border-box",
                          }}
                        />
                      );
                    })}
                  </div>

                  {/* TASK BAR */}
                  <div
                    style={{
                      position: "absolute",
                      left: offsetDays * dayWidth,
                      top: (rowHeight - barHeight) / 2,
                      width: durationDays * dayWidth,
                      height: barHeight,
                      background: isSelected
                        ? "#f97316"
                        : dependent
                        ? "#22c55e"
                        : "#2563eb",
                      borderRadius: "2px",
                      boxShadow: "inset 0 -2px 0 rgba(0,0,0,0.15)",
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default GanttChart;
