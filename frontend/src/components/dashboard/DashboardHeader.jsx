import PageHeader from "../ui/PageHeader";
import { formatDashboardDate } from "../../utils/dashboardSummary";


function DashboardHeader({ projectName, asOf }) {
  return (
    <PageHeader
      title="Project Dashboard"
      subtitle={
        <span className="dashboard-header__context">
          <strong className="dashboard-header__project">{projectName}</strong>
          <span>
            As of{" "}
            <time dateTime={asOf}>{formatDashboardDate(asOf)}</time>
          </span>
        </span>
      }
    />
  );
}

export default DashboardHeader;
