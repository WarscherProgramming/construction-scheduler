function DashboardMetricCard({
  label,
  value,
  context,
  href,
  linkLabel,
  onNavigate,
}) {
  return (
    <article className="dashboard-metric-card">
      <h3 className="dashboard-metric-card__label">{label}</h3>
      <p
        className="dashboard-metric-card__value"
        aria-label={`${label}: ${value}`}
      >
        {value}
      </p>
      {context && (
        <p className="dashboard-metric-card__context">{context}</p>
      )}
      {href && linkLabel && (
        <a
          className="dashboard-metric-card__link"
          href={href}
          onClick={(event) => {
            event.preventDefault();
            onNavigate?.();
          }}
        >
          {linkLabel}
        </a>
      )}
    </article>
  );
}

export default DashboardMetricCard;
