const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  marginTop: "20px",
};

const headerStyle = {
  padding: "10px",
  background: "#f3f4f6",
  border: "1px solid #ddd",
  textAlign: "left",
};

function RecordTable({ headers, children, label = "Project records" }) {
  return (
    <div
      className="table-scroll-region"
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      <table style={tableStyle}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col" style={headerStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export default RecordTable;
