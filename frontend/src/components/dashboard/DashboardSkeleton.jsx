import { Skeleton } from "../ui/Skeleton";


function DashboardSkeleton() {
  return (
    <section
      className="dashboard-loading"
      aria-labelledby="dashboard-loading-title"
    >
      <h2 id="dashboard-loading-title" className="visually-hidden">
        Loading project dashboard
      </h2>
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
    </section>
  );
}

export default DashboardSkeleton;
