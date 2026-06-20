import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordTable from "../components/RecordTable";
import { buttonStyle, tableCellStyle } from "../styles";

function DailyLogsPage({
  projectName,
  dailyLogs,
  projectCompanies,
  logDate,
  logCompany,
  logManpower,
  logNotes,
  formatDate,
  onBack,
  onRefresh,
  onCreate,
  onDateChange,
  onCompanyChange,
  onManpowerChange,
  onNotesChange,
}) {
  return (
    <ProjectPageLayout title={`${projectName} Daily Logs`} onBack={onBack}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Create Daily Log</h3>

        <input
          type="date"
          value={logDate}
          onChange={(event) => onDateChange(event.target.value)}
        />

        <select
          value={logCompany}
          onChange={(event) => onCompanyChange(event.target.value)}
        >
          <option value="">Select Company</option>
          {projectCompanies.map((company) => (
            <option key={company.id} value={company.name}>
              {company.name}
            </option>
          ))}
        </select>

        <select
          value={logManpower}
          onChange={(event) => onManpowerChange(event.target.value)}
        >
          <option value="">Manpower</option>
          {Array.from({ length: 50 }, (_, index) => index + 1).map((number) => (
            <option key={number} value={number}>
              {number}
            </option>
          ))}
        </select>

        <textarea
          placeholder="Notes"
          value={logNotes}
          onChange={(event) => onNotesChange(event.target.value)}
        />

        <button onClick={onCreate} style={buttonStyle}>
          Save Daily Log
        </button>
      </div>

      <button
        onClick={onRefresh}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        Refresh Logs
      </button>

      <RecordTable headers={["Date", "Company", "Manpower", "Notes"]}>
        {dailyLogs.map((log) => (
          <tr key={log.id}>
            <td style={tableCellStyle}>{formatDate(log.date)}</td>
            <td style={tableCellStyle}>{log.company}</td>
            <td style={tableCellStyle}>{log.manpower}</td>
            <td style={tableCellStyle}>{log.notes}</td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default DailyLogsPage;
