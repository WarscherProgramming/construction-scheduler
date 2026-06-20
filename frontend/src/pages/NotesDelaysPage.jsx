import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordTable from "../components/RecordTable";
import { buttonStyle, tableCellStyle } from "../styles";

function NotesDelaysPage({
  projectName,
  notesDelays,
  projectCompanies,
  noteDelayDate,
  noteDelayType,
  noteDelayCompany,
  noteDelayDescription,
  noteDelayImpact,
  formatDate,
  onBack,
  onRefresh,
  onCreate,
  onDateChange,
  onTypeChange,
  onCompanyChange,
  onDescriptionChange,
  onImpactChange,
}) {
  return (
    <ProjectPageLayout title={`${projectName} Notes & Delays`} onBack={onBack}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Create Entry</h3>

        <input
          type="date"
          value={noteDelayDate}
          onChange={(event) => onDateChange(event.target.value)}
        />
        <select
          value={noteDelayType}
          onChange={(event) => onTypeChange(event.target.value)}
        >
          <option value="Note">Note</option>
          <option value="Delay">Delay</option>
        </select>
        <select
          value={noteDelayCompany}
          onChange={(event) => onCompanyChange(event.target.value)}
        >
          <option value="">Select Company</option>
          {projectCompanies.map((company) => (
            <option key={company.id} value={company.name}>
              {company.name}
            </option>
          ))}
        </select>
        <textarea
          placeholder="Description"
          value={noteDelayDescription}
          onChange={(event) => onDescriptionChange(event.target.value)}
        />
        <textarea
          placeholder="Impact"
          value={noteDelayImpact}
          onChange={(event) => onImpactChange(event.target.value)}
        />

        <button onClick={onCreate} style={buttonStyle}>
          Save Entry
        </button>
      </div>

      <button
        onClick={onRefresh}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        Refresh Entries
      </button>

      <RecordTable
        headers={["Date", "Type", "Company", "Description", "Impact"]}
      >
        {notesDelays.map((entry) => (
          <tr key={entry.id}>
            <td style={tableCellStyle}>{formatDate(entry.date)}</td>
            <td style={tableCellStyle}>{entry.entry_type}</td>
            <td style={tableCellStyle}>{entry.company}</td>
            <td style={tableCellStyle}>{entry.description}</td>
            <td style={tableCellStyle}>{entry.impact}</td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default NotesDelaysPage;
