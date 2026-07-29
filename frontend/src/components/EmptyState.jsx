function EmptyState({ title, description, announce = true }) {
  return (
    <div className="empty-state" role={announce ? "status" : undefined}>
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </div>
  );
}

export default EmptyState;
