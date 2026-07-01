const PREDECESSOR_PATTERN = /^(\d+(?:\.\d+)*)((?:SS)?(?:\+\d+D?)?)$/i;

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
    suffix: match[2],
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

export function formatPredecessorForSchedule(reference, tasks) {
  const parsed = parsePredecessor(reference);

  if (!parsed) {
    return reference || "";
  }

  // Stored references use database task ids (always plain integers).
  const wbsNumber = buildWbsMap(tasks).get(Number(parsed.code));

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
      error: "Use a schedule ID such as 2, 1.2, 2+3, or 1.2SS+4.",
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
