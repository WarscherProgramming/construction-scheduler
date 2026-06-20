function parseCurrencyAmount(value) {
  const amount = Number(String(value || "0").replace(/[$,\s]/g, ""));
  return Number.isFinite(amount) ? amount : 0;
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
