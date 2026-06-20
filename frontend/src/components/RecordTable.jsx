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

function RecordTable({ headers, children }) {
  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          {headers.map((header) => (
            <th key={header} style={headerStyle}>
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}

export default RecordTable;
