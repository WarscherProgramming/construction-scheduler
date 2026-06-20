import FormField from "../components/FormField";
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
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Create Daily Log</h3>

        <FormField label="Date" htmlFor="daily-log-date" required>
          <input
            id="daily-log-date"
            className="field-control"
            type="date"
            required
            value={logDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>

        <FormField label="Company" htmlFor="daily-log-company" required>
          <select
            id="daily-log-company"
            className="field-control"
            required
            value={logCompany}
            onChange={(event) => onCompanyChange(event.target.value)}
          >
            <option value="">Select company</option>
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name}>
                {company.name}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Manpower" htmlFor="daily-log-manpower" required>
          <select
            id="daily-log-manpower"
            className="field-control"
            required
            value={logManpower}
            onChange={(event) => onManpowerChange(event.target.value)}
          >
            <option value="">Select manpower</option>
            {Array.from({ length: 50 }, (_, index) => index + 1).map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Notes" htmlFor="daily-log-notes">
          <textarea
            id="daily-log-notes"
            className="field-control"
            value={logNotes}
            onChange={(event) => onNotesChange(event.target.value)}
          />
        </FormField>

        <button type="submit" style={buttonStyle}>
          Save Daily Log
        </button>
      </form>

      <button
        onClick={onRefresh}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        Refresh Logs
      </button>

      <RecordTable
        label="Daily logs"
        headers={["Date", "Company", "Manpower", "Notes"]}
      >
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
