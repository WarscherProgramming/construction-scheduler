export function getTaskDepthFromList(tasks, task) {
  const taskMap = new Map(tasks.map((candidate) => [candidate.id, candidate]));
  const visited = new Set();
  let depth = 0;
  let parentId = task?.parent_task_id;

  while (parentId && !visited.has(parentId)) {
    visited.add(parentId);
    const parent = taskMap.get(parentId);

    if (!parent) break;

    depth += 1;
    parentId = parent.parent_task_id;
  }

  return depth;
}

export function findIndentParent(tasks, taskId) {
  const taskIndex = tasks.findIndex((task) => task.id === taskId);

  if (taskIndex <= 0) return null;

  const taskDepth = getTaskDepthFromList(tasks, tasks[taskIndex]);

  for (let index = taskIndex - 1; index >= 0; index -= 1) {
    const candidate = tasks[index];
    const candidateDepth = getTaskDepthFromList(tasks, candidate);

    if (candidateDepth === taskDepth) return candidate;
    if (candidateDepth < taskDepth) return null;
  }

  return null;
}
