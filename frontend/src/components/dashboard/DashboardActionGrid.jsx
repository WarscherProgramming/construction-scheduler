import AttentionRequired from "./AttentionRequired";
import UpcomingSchedule from "./UpcomingSchedule";


function DashboardActionGrid({
  dashboard,
  projectId,
  onNavigate,
}) {
  const attentionItems = Array.isArray(dashboard.attention_items)
    ? dashboard.attention_items
    : [];
  const upcomingTasks = Array.isArray(dashboard.upcoming_tasks)
    ? dashboard.upcoming_tasks
    : [];

  return (
    <div className="dashboard-action-grid">
      <AttentionRequired
        items={attentionItems}
        projectId={projectId}
        onNavigate={onNavigate}
      />
      <UpcomingSchedule
        tasks={upcomingTasks}
        hasScheduleTasks={Number(dashboard.schedule?.task_count) > 0}
        projectId={projectId}
        onNavigate={onNavigate}
      />
    </div>
  );
}

export default DashboardActionGrid;
