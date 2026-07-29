import { buildAppHash } from "../../utils/navigation";
import {
  formatDashboardDuration,
  formatOptionalDashboardDate,
} from "../../utils/dashboardSummary";


function UpcomingTaskItem({
  task,
  projectId,
  onNavigate,
}) {
  const name =
    typeof task?.name === "string" && task.name.trim()
      ? task.name.trim()
      : `Task ${task?.id || ""}`.trim();
  const startDate = formatOptionalDashboardDate(task?.start_date);
  const endDate = formatOptionalDashboardDate(task?.end_date);
  const duration = formatDashboardDuration(task?.duration);

  return (
    <li className="dashboard-action-item">
      <h3>{name}</h3>

      <div className="dashboard-action-item__details">
        {startDate && (
          <p className="dashboard-action-item__detail">
            <span>Starts</span>{" "}
            <time dateTime={task.start_date}>{startDate}</time>
          </p>
        )}
        {endDate && (
          <p className="dashboard-action-item__detail">
            <span>Ends</span>{" "}
            <time dateTime={task.end_date}>{endDate}</time>
          </p>
        )}
        {duration && (
          <p className="dashboard-action-item__detail">{duration}</p>
        )}
      </div>

      {projectId && (
        <a
          className="dashboard-action-item__link"
          href={buildAppHash("scheduler", projectId)}
          onClick={(event) => {
            event.preventDefault();
            onNavigate?.("scheduler");
          }}
        >
          View Schedule
        </a>
      )}
    </li>
  );
}

export default UpcomingTaskItem;
