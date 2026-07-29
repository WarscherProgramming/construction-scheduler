import EmptyState from "../EmptyState";
import RecentUpdateItem from "./RecentUpdateItem";


function RecentUpdates({
  updates,
  projectId,
  onNavigate,
}) {
  return (
    <section
      className="dashboard-insight-section dashboard-recent-updates"
      aria-labelledby="dashboard-recent-updates-title"
    >
      <div className="dashboard-insight-section__header">
        <h2 id="dashboard-recent-updates-title">Recent Updates</h2>
        <p>Recently updated project records.</p>
      </div>

      {updates.length === 0 ? (
        <EmptyState
          title="No recent record updates are available."
          description="This section reflects update timestamps from supported project records."
          announce={false}
        />
      ) : (
        <ul className="dashboard-recent-updates__list">
          {updates.map((update, index) => (
            <RecentUpdateItem
              key={`${update?.resource_type || "unknown"}-${update?.record_id || index}`}
              update={update}
              projectId={projectId}
              onNavigate={onNavigate}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default RecentUpdates;
