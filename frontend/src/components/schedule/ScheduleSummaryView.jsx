import Button from "../ui/Button";
import Card from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";
import useScheduleHealth from "../../hooks/useScheduleHealth";
import { formatDisplayDate } from "../../utils/date";


function metricValue(value, fallback = "Not available") {
  return value == null ? fallback : value;
}


function ScheduleSummaryView({
  projectId,
  onRequestError,
  onDownloadCurrent,
  onDownloadExecutive,
  isDownloadingCurrent,
  isDownloadingExecutive,
}) {
  const { health, error, isLoading, retry } = useScheduleHealth({
    projectId,
    enabled: true,
    onError: onRequestError,
  });

  if (isLoading) {
    return (
      <div className="schedule-summary-view" aria-label="Loading schedule summary">
        <Skeleton style={{ height: "8rem" }} />
        <Skeleton style={{ height: "14rem" }} />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="schedule-summary-error">
        <h2>Schedule summary unavailable</h2>
        <p>The current schedule remains available. Try loading this summary again.</p>
        <Button onClick={retry}>Retry Schedule Summary</Button>
      </Card>
    );
  }

  if (!health) return null;
  const summary = health.executive_summary;
  const metrics = [
    ["Current Forecast Finish", formatDisplayDate(summary.current_forecast_finish)],
    ["Finish Variance", summary.project_finish_variance_workdays == null ? "No baseline comparison" : `${summary.project_finish_variance_workdays} workdays`],
    ["Leaf Tasks", summary.total_leaf_tasks],
    ["Not Started", summary.not_started_tasks],
    ["In Progress", summary.in_progress_tasks],
    ["Completed", summary.completed_tasks],
    ["Slipped", summary.slipped_tasks],
    ["Newly Critical", summary.newly_critical_tasks],
    ["Negative Float", summary.negative_float_tasks],
    ["Out of Sequence", summary.out_of_sequence_tasks],
    ["Milestones Due", summary.milestones_due_next_21_days],
    ["Blocked Look-Ahead", summary.blocked_look_ahead_items],
    ["Labor Conflict Days", summary.labor_overallocated_days],
    ["Equipment Conflict Days", summary.equipment_overallocated_days],
    ["Unassigned Tasks", summary.unassigned_executable_tasks],
  ];

  return (
    <div className="schedule-summary-view">
      <section className="schedule-health-panel" aria-labelledby="schedule-health-title">
        <div>
          <p className="schedule-health-category">{health.category} schedule health</p>
          <h2 id="schedule-health-title">{health.summary}</h2>
          <p>
            Data Date {formatDisplayDate(health.data_date)}. Baseline: {health.baseline?.name || "none selected or active"}.
          </p>
        </div>
        <div className="schedule-report-actions no-print" aria-label="Schedule report downloads">
          <Button onClick={onDownloadCurrent} disabled={isDownloadingCurrent} aria-busy={isDownloadingCurrent}>
            {isDownloadingCurrent ? "Downloading..." : "Download Current Schedule PDF"}
          </Button>
          <Button onClick={onDownloadExecutive} disabled={isDownloadingExecutive} aria-busy={isDownloadingExecutive}>
            {isDownloadingExecutive ? "Downloading..." : "Download Executive Schedule Report"}
          </Button>
        </div>
      </section>

      <section aria-labelledby="executive-metrics-title">
        <h2 id="executive-metrics-title">Executive Schedule Metrics</h2>
        <dl className="schedule-summary-metrics">
          {metrics.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{metricValue(value)}</dd></div>
          ))}
        </dl>
      </section>

      <div className="schedule-summary-columns">
        <section aria-labelledby="health-reasons-title">
          <h2 id="health-reasons-title">Health Reasons</h2>
          {health.reasons.length ? (
            <ul className="schedule-health-list">
              {health.reasons.map((reason) => (
                <li key={reason.code}>
                  <strong>{reason.severity}: {reason.label}</strong>
                </li>
              ))}
            </ul>
          ) : <p>No health reasons are active.</p>}
        </section>

        <section aria-labelledby="schedule-attention-title">
          <h2 id="schedule-attention-title">Top Attention Items</h2>
          {health.top_attention_items.length ? (
            <ul className="schedule-attention-list">
              {health.top_attention_items.map((item, index) => (
                <li key={`${item.source}:${item.task_id || index}:${item.code}`}>
                  <strong>{item.title}</strong>
                  <span>{item.severity}: {item.reason}</span>
                  {item.due_date && <small>{formatDisplayDate(item.due_date)}</small>}
                </li>
              ))}
            </ul>
          ) : <p>No schedule attention items are active.</p>}
        </section>
      </div>
    </div>
  );
}


export default ScheduleSummaryView;
