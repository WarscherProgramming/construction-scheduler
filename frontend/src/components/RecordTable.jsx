import { Children } from "react";

import LoadingState from "./LoadingState";


const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  marginTop: "20px",
};

const headerStyle = {
  padding: "10px",
  background: "var(--surface-muted)",
  border: "1px solid var(--border)",
  color: "var(--text-h)",
  textAlign: "left",
};

function RecordTable({
  headers,
  children,
  label = "Project records",
  emptyMessage = "No records yet.",
  isLoading = false,
  loadingMessage = "Loading records…",
}) {
  const hasRows = Children.count(children) > 0;

  return (
    <div
      className="table-scroll-region"
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      {isLoading && <LoadingState message={loadingMessage} />}
      <table className="record-table" style={tableStyle}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col" style={headerStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {hasRows ? (
            children
          ) : isLoading ? (
            null
          ) : (
            <tr>
              <td
                className="table-empty-cell"
                colSpan={headers.length}
                data-label=""
              >
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default RecordTable;
