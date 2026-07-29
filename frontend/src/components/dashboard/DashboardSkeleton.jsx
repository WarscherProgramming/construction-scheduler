import { Skeleton } from "../ui/Skeleton";


function DashboardSkeleton() {
  return (
    <section
      className="dashboard-loading"
      aria-labelledby="dashboard-loading-title"
    >
      <span id="dashboard-loading-title" className="visually-hidden">
        Loading project dashboard
      </span>
      <p role="status">Loading project summary…</p>
      <div className="dashboard-summary-grid" aria-hidden="true">
        {Array.from({ length: 8 }, (_, index) => (
          <div className="dashboard-metric-card" key={index}>
            <Skeleton className="skeleton--sub" />
            <Skeleton className="skeleton--value" />
            <Skeleton className="skeleton--line" />
          </div>
        ))}
      </div>
      <div className="dashboard-action-grid" aria-hidden="true">
        {Array.from({ length: 2 }, (_, sectionIndex) => (
          <div
            className="dashboard-action-section dashboard-action-section--loading"
            key={sectionIndex}
          >
            <Skeleton className="skeleton--sub" />
            <Skeleton className="skeleton--line" />
            {Array.from({ length: 3 }, (_, rowIndex) => (
              <div
                className="dashboard-action-skeleton-row"
                key={rowIndex}
              >
                <Skeleton className="skeleton--sub" />
                <Skeleton className="skeleton--line" />
                <Skeleton className="skeleton--line" />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="dashboard-insights-grid" aria-hidden="true">
        <div className="dashboard-insight-section">
          <Skeleton className="skeleton--sub" />
          <Skeleton className="skeleton--line" />
          <div className="dashboard-workflow-grid">
            {Array.from({ length: 4 }, (_, index) => (
              <div className="dashboard-workflow-card" key={index}>
                <Skeleton className="skeleton--sub" />
                <Skeleton className="skeleton--value" />
                <Skeleton className="skeleton--line" />
                <Skeleton className="skeleton--line" />
              </div>
            ))}
          </div>
        </div>
        <div className="dashboard-insight-section">
          <Skeleton className="skeleton--sub" />
          <Skeleton className="skeleton--line" />
          {Array.from({ length: 3 }, (_, index) => (
            <div className="dashboard-recent-update-skeleton" key={index}>
              <Skeleton className="skeleton--sub" />
              <Skeleton className="skeleton--line" />
              <Skeleton className="skeleton--line" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default DashboardSkeleton;
