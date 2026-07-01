function RecordCell({ label, children, className = "" }) {
  return (
    <td
      className={`record-cell ${className}`.trim()}
      data-label={label}
    >
      {children}
    </td>
  );
}

export default RecordCell;
