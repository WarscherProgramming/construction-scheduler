function StatusBadge({ value }) {
  const tone = String(value || "Unknown")
    .toLowerCase()
    .replace(/\s+/g, "-");

  return <span className={`status-badge status-${tone}`}>{value || "Unknown"}</span>;
}

export default StatusBadge;
