function GanttChart({ tasks, selectedTaskId }) {
  if (!tasks.length) return <p>No tasks yet</p>;

  const MS_PER_DAY = 1000 * 60 * 60 * 24;

  // 🔥 FIX: parse dates in LOCAL time (no UTC drift)
  const parseDate = (date) => {
    if (!date) return null;

    // MM/DD/YYYY
    if (date.includes("/")) {
      const [m, d, y] = date.split("/").map(Number);
      return new Date(y, m - 1, d);
    }

    // YYYY-MM-DD fallback
    const [y, m, d] = date.split("-").map(Number);
    return new Date(y, m - 1, d);
  };

  const parsePredecessor = (value) => {
    if (!value) return null;

    const match = value
      .replace(/\s/g, "")
      .match(/^(\d+)(SS)?(?:\+(\d+))?/i);

    if (!match) return null;

    return {
      index: Number(match[1]),
      relation: match[2] ? "SS" : "FS",
      lag: match[3] ? Number(match[3]) : 0,
    };
  };

  // 🔥 Convert everything to timestamps
  const scheduledTasks = tasks.filter(
    (t) => t.start_date && t.end_date
  );

  if (!scheduledTasks.length) {
    return <p>No scheduled tasks yet</p>;
  }

  const taskStartTimes = scheduledTasks.map((t) =>
    parseDate(t.start_date).getTime()
  );

  const taskEndTimes = scheduledTasks.map((t) =>
    parseDate(t.end_date).getTime()
  );

  const projectStartMs = Math.min(...taskStartTimes);
  const projectEndMs = Math.max(...taskEndTimes);

  const projectStartDate = new Date(projectStartMs);
  projectStartDate.setHours(0, 0, 0, 0);

  const totalDays = Math.ceil(
    (projectEndMs - projectStartMs) / MS_PER_DAY
  ) + 1;

  const isDependent = (task, selectedId) => {
    let current = task;

    while (current.predecessor) {
      const parsed = parsePredecessor(current.predecessor);

      if (!parsed) break;

      const predecessorTask = tasks[parsed.index - 1];

      if (!predecessorTask) break;

      if (predecessorTask.id === selectedId) {
        return true;
      }

      current = predecessorTask;
    }

    return false;
  };
  const dayWidth = 30;
  const rowHeight = 56;
  const labelHeight = 24;
  const barHeight = 20;

  // 🔥 MONTH GROUPING
  const months = [];
  let currentMonth = null;
  let count = 0;

  for (let i = 0; i < totalDays; i++) {
    const date = new Date(projectStartDate);
    date.setDate(date.getDate() + i);

    const month = date.toLocaleString("default", { month: "short" });

    if (month !== currentMonth) {
      if (currentMonth !== null) {
        months.push({ name: currentMonth, days: count });
      }
      currentMonth = month;
      count = 1;
    } else {
      count++;
    }
  }

  months.push({ name: currentMonth, days: count });

  return (
    <div style={{ marginTop: "30px" }}>
      <h2>Gantt Chart</h2>

      <div style={{ overflowX: "auto", position: "relative", zIndex: 1 }}>
        <div style={{ width: totalDays * dayWidth }}>

          {/* MONTH HEADER */}
          <div style={{ display: "flex" }}>
            {months.map((m, i) => (
              <div
                key={i}
                style={{
                  width: m.days * dayWidth,
                  textAlign: "center",
                  fontWeight: "bold",
                  borderRight: "1px solid #ccc",
                  boxSizing: "border-box",
                  height: rowHeight,
                  position: "relative",
                }}
              >
                {m.name}
              </div>
            ))}
          </div>

          {/* DAY ROW */}
          <div style={{ display: "flex", marginBottom: "10px" }}>
            {Array.from({ length: totalDays }).map((_, i) => {
              const date = new Date(projectStartDate);
              date.setDate(date.getDate() + i);

              return (
                <div
                  key={i}
                  style={{
                    width: dayWidth,
                    fontSize: "10px",
                    borderRight: "1px solid #ccc",
                    textAlign: "center",
                    boxSizing: "border-box",
                    height: rowHeight,
                    position: "relative",
                  }}
                >
                  {date.getDate()}
                </div>
              );
            })}
          </div>

          {/* TASK BARS */}
          {scheduledTasks.map((task) => {
            if (!task.start_date || !task.end_date) return null;

            const startMs = parseDate(task.start_date).getTime();
            const endMs = parseDate(task.end_date).getTime();

            const offsetDays = Math.round(
              (startMs - projectStartMs) / MS_PER_DAY
            );

            const durationDays =
              Math.round((endMs - startMs) / MS_PER_DAY) + 1;

            const isSelected = task.id === selectedTaskId;
            const dependent = isDependent(task, selectedTaskId);

            const barLeft = offsetDays * dayWidth;
            const barWidth = durationDays * dayWidth;
            const barRight = barLeft + barWidth;
            return (
              <div key={task.id} style={{ height: rowHeight, position: "relative" }}>
                <div style={{ height: labelHeight, textAlign: "center"}}>{task.name}</div>

                <div
                  style={{
                    display: "flex",
                    height: barHeight,
                    background: "#eee",
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      marginLeft: offsetDays * dayWidth,
                      width: durationDays * dayWidth,
                      height: "100%",
                      background: isSelected
                        ? "orange"
                        : dependent
                        ? "lightgreen"
                        : "steelblue",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default GanttChart;