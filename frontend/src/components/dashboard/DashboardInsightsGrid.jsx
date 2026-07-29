import RecentUpdates from "./RecentUpdates";
import WorkflowAnalytics from "./WorkflowAnalytics";


function DashboardInsightsGrid({
  dashboard,
  projectId,
  onNavigate,
}) {
  const recentUpdates = Array.isArray(dashboard.recent_updates)
    ? dashboard.recent_updates
    : [];

  return (
    <div className="dashboard-insights-grid">
      <WorkflowAnalytics
        dashboard={dashboard}
        projectId={projectId}
        onNavigate={onNavigate}
      />
      <RecentUpdates
        updates={recentUpdates}
        projectId={projectId}
        onNavigate={onNavigate}
      />
    </div>
  );
}

export default DashboardInsightsGrid;
