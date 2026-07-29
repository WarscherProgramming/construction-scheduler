import { buildAppHash } from "../../utils/navigation";
import {
  calculateDistributionValue,
  formatDashboardCount,
} from "../../utils/dashboardSummary";


function WorkflowSummaryCard({
  title,
  total,
  metrics,
  emptyMessage,
  values,
  page,
  linkLabel,
  projectId,
  onNavigate,
}) {
  const displayedTotal = formatDashboardCount(total);
  const numericTotal = Number(total);
  const hasNoRecords =
    total !== null &&
    total !== undefined &&
    total !== "" &&
    Number.isFinite(numericTotal) &&
    numericTotal === 0;

  return (
    <article className="dashboard-workflow-card">
      <h3>{title}</h3>
      <p className="dashboard-workflow-card__total">
        <strong>{displayedTotal}</strong> total
      </p>

      {hasNoRecords ? (
        <p className="dashboard-workflow-card__empty">{emptyMessage}</p>
      ) : (
        <ul className="dashboard-workflow-metrics">
          {metrics.map((metric) => {
            const displayedCount = formatDashboardCount(metric.count);
            const width = calculateDistributionValue(
              metric.count,
              total
            );

            return (
              <li key={metric.label}>
                <div className="dashboard-workflow-metric__text">
                  <span>{metric.label}</span>
                  <strong>{displayedCount}</strong>
                </div>
                <div
                  className="dashboard-workflow-metric__track"
                  aria-hidden="true"
                >
                  <span style={{ width: `${width}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {values?.length > 0 && (
        <dl className="dashboard-workflow-values">
          {values.map((value) => (
            <div key={value.label}>
              <dt>{value.label}</dt>
              <dd>{value.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <a
        className="dashboard-insight-link"
        href={buildAppHash(page, projectId)}
        onClick={(event) => {
          event.preventDefault();
          onNavigate?.(page);
        }}
      >
        {linkLabel}
      </a>
    </article>
  );
}

export default WorkflowSummaryCard;
