const PREDECESSOR_PATTERN =
  /^(\d+(?:\.\d+)*)(?:(FS|SS|FF|SF))?([+-]\d+D?)?$/i;

function parsePredecessor(reference) {
  const normalized = String(reference ?? "").trim().toUpperCase();

  if (!normalized) {
    return null;
  }

  const match = normalized.match(PREDECESSOR_PATTERN);

  if (!match) {
    return null;
  }

  return {
    code: match[1],
    dependencyType: match[2] || "FS",
    lagSuffix: match[3] || "",
    suffix: `${match[2] || ""}${match[3] || ""}`,
  };
}

/**
 * Hierarchical WBS numbering derived from display order and parentage:
 * root tasks are 1, 2, 3…; children are 1.1, 1.2, 2.1; deeper levels 1.1.1.
 * Returns Map(taskId → WBS string). Tasks whose parent has not appeared
 * earlier in the list fall back to root-level numbering.
 */
export function buildWbsMap(tasks) {
  const wbs = new Map();
  const childCounts = new Map();

  for (const task of tasks) {
    const parentId = task.parent_task_id ?? null;
    const parentWbs = parentId === null ? null : wbs.get(parentId) ?? null;
    const countKey = parentWbs === null ? "__root__" : parentWbs;

    const count = (childCounts.get(countKey) || 0) + 1;
    childCounts.set(countKey, count);

    wbs.set(task.id, parentWbs === null ? String(count) : `${parentWbs}.${count}`);
  }

  return wbs;
}

/** The task's WBS number (e.g. "2" or "1.3.1"), or null if unknown. */
export function getScheduleTaskNumber(tasks, taskId) {
  return buildWbsMap(tasks).get(taskId) ?? null;
}

export function formatPredecessorForSchedule(
  reference,
  tasks,
  wbsMap = buildWbsMap(tasks)
) {
  const parsed = parsePredecessor(reference);

  if (!parsed) {
    return reference || "";
  }

  // Stored references use database task ids (always plain integers).
  const wbsNumber = wbsMap.get(Number(parsed.code));

  if (!wbsNumber) {
    return reference;
  }

  return `${wbsNumber}${parsed.suffix}`;
}

export function formatPredecessorForApi(reference, tasks) {
  const normalized = String(reference ?? "").trim().toUpperCase();

  if (!normalized) {
    return { value: null, error: null };
  }

  const parsed = parsePredecessor(normalized);

  if (!parsed) {
    return {
      value: null,
      error:
        "Use a schedule ID such as 2, 1.2FS-2, 2SS+3, 1.2FF, or 3SF+1.",
    };
  }

  const wbsMap = buildWbsMap(tasks);
  const predecessor = tasks.find(
    (task) => wbsMap.get(task.id) === parsed.code
  );

  if (!predecessor) {
    return {
      value: null,
      error: `No task has schedule ID ${parsed.code}. Use the ID shown in the first column.`,
    };
  }

  return {
    value: `${predecessor.id}${parsed.suffix}`,
    error: null,
  };
}

export function getTaskDependencies(task) {
  if (Array.isArray(task?.dependencies) && task.dependencies.length) {
    return task.dependencies;
  }
  if (task?.predecessor_task_id == null) return [];
  return [
    {
      predecessor_task_id: task.predecessor_task_id,
      dependency_type: task.dependency_type || "FS",
      lag_days: task.lag_days || 0,
    },
  ];
}

export function formatDependencyForSchedule(
  dependency,
  tasks,
  wbsMap = buildWbsMap(tasks)
) {
  const scheduleId = wbsMap.get(Number(dependency.predecessor_task_id));
  if (!scheduleId) return String(dependency.predecessor_task_id);
  const type = dependency.dependency_type || "FS";
  const lag = Number(dependency.lag_days) || 0;
  const lagSuffix = lag === 0 ? "" : `${lag > 0 ? "+" : ""}${lag}`;
  return `${scheduleId}${type}${lagSuffix}`;
}

export function formatDependenciesForSchedule(
  task,
  tasks,
  wbsMap = buildWbsMap(tasks)
) {
  return getTaskDependencies(task)
    .map((dependency) =>
      formatDependencyForSchedule(dependency, tasks, wbsMap)
    )
    .join(", ");
}
