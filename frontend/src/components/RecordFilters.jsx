function RecordFilters({ title = "Filter records", resultCount, children }) {
  return (
    <section className="record-filters" aria-labelledby="record-filters-title">
      <div className="record-filters-heading">
        <h2 id="record-filters-title">{title}</h2>
        <span aria-live="polite">
          {resultCount} {resultCount === 1 ? "record" : "records"}
        </span>
      </div>
      <div className="record-filter-controls">{children}</div>
    </section>
  );
}

export default RecordFilters;
