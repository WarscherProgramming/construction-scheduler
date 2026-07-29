import EmptyState from "../EmptyState";
import AttentionItem from "./AttentionItem";


function AttentionRequired({
  items,
  projectId,
  onNavigate,
}) {
  return (
    <section
      className="dashboard-action-section"
      aria-labelledby="dashboard-attention-title"
    >
      <div className="dashboard-action-section__header">
        <h2 id="dashboard-attention-title">Attention Required</h2>
        <p>Items that may need review or follow-up.</p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No attention items were identified for this dashboard date."
          description="This reflects the current dashboard rules and is not a complete risk assessment."
        />
      ) : (
        <ul className="dashboard-action-list">
          {items.map((item, index) => (
            <AttentionItem
              key={`${item?.resource_type || "unknown"}-${item?.record_id || index}`}
              item={item}
              projectId={projectId}
              onNavigate={onNavigate}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default AttentionRequired;
