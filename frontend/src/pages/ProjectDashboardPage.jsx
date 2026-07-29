import DashboardActionGrid from "../components/dashboard/DashboardActionGrid";
import DashboardEmptyState from "../components/dashboard/DashboardEmptyState";
import DashboardErrorState from "../components/dashboard/DashboardErrorState";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import DashboardSkeleton from "../components/dashboard/DashboardSkeleton";
import DashboardSummaryGrid from "../components/dashboard/DashboardSummaryGrid";
import ProjectLayout from "../components/ui/ProjectLayout";
import useProjectDashboard from "../hooks/useProjectDashboard";


function ProjectDashboardPage({
  projectId,
  projectName = "Project",
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const {
    dashboard,
    isLoading,
    error,
    retry,
    asOf,
  } = useProjectDashboard({
    projectId,
    onError: onRequestError,
  });

  const displayedProjectName = dashboard?.project?.name || projectName;

  return (
    <ProjectLayout
      projectName={displayedProjectName}
      activeId="projectDashboard"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="dashboard-page"
    >
      <DashboardHeader
        projectName={displayedProjectName}
        asOf={asOf}
      />

      {!projectId ? (
        <DashboardEmptyState />
      ) : isLoading ? (
        <DashboardSkeleton />
      ) : error ? (
        <DashboardErrorState onRetry={retry} />
      ) : dashboard ? (
        <>
          <DashboardSummaryGrid
            dashboard={dashboard}
            projectId={projectId}
            onNavigate={onNavigate}
          />
          <DashboardActionGrid
            dashboard={dashboard}
            projectId={projectId}
            onNavigate={onNavigate}
          />
        </>
      ) : null}
    </ProjectLayout>
  );
}

export default ProjectDashboardPage;
