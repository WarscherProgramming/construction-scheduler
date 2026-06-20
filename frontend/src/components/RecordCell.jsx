import { tableCellStyle } from "../styles";


function RecordCell({ label, children, className = "" }) {
  return (
    <td
      className={`record-cell ${className}`.trim()}
      data-label={label}
      style={tableCellStyle}
    >
      {children}
    </td>
  );
}

export default RecordCell;
