function EmptyState({ title, description }) {
  return (
    <div className="empty-state" role="status">
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </div>
  );
}

export default EmptyState;
