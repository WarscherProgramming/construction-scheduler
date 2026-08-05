import { parseLocalDateInputValue } from "./date";


export const PROGRESS_STATUS_LABELS = {
  not_started: "Not Started",
  in_progress: "In Progress",
  completed: "Completed",
};


export function formatProgressStatus(value) {
  return PROGRESS_STATUS_LABELS[value] || "Not Started";
}


export function isTaskStatused(task) {
  return (task?.progress_status || "not_started") !== "not_started";
}


export function isValidStatusDate(value, dataDate) {
  return Boolean(
    parseLocalDateInputValue(value) &&
      parseLocalDateInputValue(dataDate) &&
      value <= dataDate
  );
}


export function buildScheduleProgressSummary(tasks, dataDate) {
  const parentIds = new Set(
    tasks
      .map((task) => task.parent_task_id)
      .filter((id) => id !== null && id !== undefined)
  );
  const leaves = tasks.filter((task) => !parentIds.has(task.id));
  const denominator = leaves.reduce(
    (total, task) => total + Number(task.duration || 0),
    0
  );
  const weighted = leaves.reduce(
    (total, task) =>
      total +
      Number(task.duration || 0) * Number(task.percent_complete || 0),
    0
  );

  return {
    total_leaf_tasks: leaves.length,
    not_started_count: leaves.filter(
      (task) => (task.progress_status || "not_started") === "not_started"
    ).length,
    in_progress_count: leaves.filter(
      (task) => task.progress_status === "in_progress"
    ).length,
    completed_count: leaves.filter(
      (task) => task.progress_status === "completed"
    ).length,
    out_of_sequence_count: leaves.filter((task) => task.out_of_sequence)
      .length,
    percent_complete_weighted: denominator
      ? Math.round((weighted / denominator) * 10) / 10
      : 0,
    data_date: dataDate || null,
    forecast_project_finish:
      leaves
        .map((task) => task.end_date)
        .filter(Boolean)
        .sort()
        .at(-1) || null,
  };
}
