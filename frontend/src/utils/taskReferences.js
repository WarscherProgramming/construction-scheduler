const PREDECESSOR_PATTERN = /^(\d+)((?:SS)?(?:\+\d+D?)?)$/i;

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
    taskNumber: Number(match[1]),
    suffix: match[2],
  };
}

export function getScheduleTaskNumber(tasks, taskId) {
  const index = tasks.findIndex((task) => task.id === taskId);
  return index === -1 ? null : index + 1;
}

export function formatPredecessorForSchedule(reference, tasks) {
  const parsed = parsePredecessor(reference);

  if (!parsed) {
    return reference || "";
  }

  const scheduleNumber = getScheduleTaskNumber(tasks, parsed.taskNumber);

  if (scheduleNumber === null) {
    return reference;
  }

  return `${scheduleNumber}${parsed.suffix}`;
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
      error: "Use a schedule ID such as 1, 1+3, 1SS, or 1SS+4.",
    };
  }

  const predecessor = tasks[parsed.taskNumber - 1];

  if (!predecessor) {
    return {
      value: null,
      error: `Predecessor must use a schedule ID between 1 and ${tasks.length}.`,
    };
  }

  return {
    value: `${predecessor.id}${parsed.suffix}`,
    error: null,
  };
}
