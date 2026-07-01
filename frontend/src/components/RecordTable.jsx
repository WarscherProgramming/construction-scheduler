import { Children } from "react";

import { SkeletonPanel } from "./ui/Skeleton";

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
      {isLoading && (
        <SkeletonPanel
          label={loadingMessage}
          lines={4}
          className="skeleton-panel--table"
        />
      )}
      <table className="data-table record-table">
        <caption className="visually-hidden">{label}</caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
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
