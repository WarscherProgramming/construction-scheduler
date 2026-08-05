import { buildAppHash } from "../../utils/navigation";
import { formatDisplayDate } from "../../utils/date";
import Card from "../ui/Card";


function ScheduleHealthCard({ health, projectId, onNavigate }) {
  return (
    <section aria-labelledby="dashboard-schedule-health-title">
      <Card className="dashboard-schedule-health">
        <div>
          <p className="dashboard-schedule-health-category">{health.category} schedule health</p>
          <h2 id="dashboard-schedule-health-title">Schedule Health</h2>
          <p>{health.summary}</p>
          <p>
            Data Date {formatDisplayDate(health.data_date)}. {health.baseline ? `Compared with ${health.baseline.name}.` : "No active comparison baseline."}
          </p>
        </div>
        <dl>
          <div><dt>Finish Variance</dt><dd>{health.metrics.project_finish_variance_workdays == null ? "N/A" : `${health.metrics.project_finish_variance_workdays} workdays`}</dd></div>
          <div><dt>Blocked Work</dt><dd>{health.metrics.blocked_look_ahead_items}</dd></div>
          <div><dt>Resource Conflicts</dt><dd>{health.metrics.resource_overallocated_days}</dd></div>
          <div><dt>Health Reasons</dt><dd>{health.reasons.length}</dd></div>
        </dl>
        <a
          href={buildAppHash("scheduler", projectId)}
          onClick={(event) => {
            event.preventDefault();
            onNavigate("scheduler");
          }}
        >
          View Schedule Summary
        </a>
      </Card>
    </section>
  );
}


export default ScheduleHealthCard;
