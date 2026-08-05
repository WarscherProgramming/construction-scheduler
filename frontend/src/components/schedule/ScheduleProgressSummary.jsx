import { formatDisplayDate } from "../../utils/date";
import { buildScheduleProgressSummary } from "../../utils/scheduleProgress";


function ScheduleProgressSummary({
  summary,
  tasks,
  dataDate,
  isLoading = false,
}) {
  if (isLoading) {
    return (
      <section
        className="schedule-progress-summary"
        aria-labelledby="schedule-progress-summary-title"
      >
        <div className="schedule-progress-summary__heading">
          <div>
            <h2 id="schedule-progress-summary-title">Schedule Progress</h2>
            <p role="status">Loading schedule progress...</p>
          </div>
        </div>
      </section>
    );
  }

  const metrics = summary || buildScheduleProgressSummary(tasks, dataDate);
  const values = [
    ["Complete", `${metrics.percent_complete_weighted}%`],
    ["Not Started", metrics.not_started_count],
    ["In Progress", metrics.in_progress_count],
    ["Completed", metrics.completed_count],
    ["Out of Sequence", metrics.out_of_sequence_count],
    [
      "Forecast Finish",
      metrics.forecast_project_finish
        ? formatDisplayDate(metrics.forecast_project_finish)
        : "Unavailable",
    ],
  ];

  return (
    <section
      className="schedule-progress-summary"
      aria-labelledby="schedule-progress-summary-title"
    >
      <div className="schedule-progress-summary__heading">
        <div>
          <h2 id="schedule-progress-summary-title">Schedule Progress</h2>
          <p>
            Status through {formatDisplayDate(metrics.data_date || dataDate)}.
          </p>
        </div>
        <span>{metrics.total_leaf_tasks} leaf tasks</span>
      </div>
      <dl>
        {values.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default ScheduleProgressSummary;
