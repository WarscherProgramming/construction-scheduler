import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordTable from "../components/RecordTable";
import { buttonStyle, tableCellStyle } from "../styles";

function InspectionsPage({
  projectName,
  inspections,
  inspectionDate,
  inspectionType,
  inspectionStatus,
  formatDate,
  onBack,
  onRefresh,
  onCreate,
  onDateChange,
  onTypeChange,
  onStatusChange,
}) {
  return (
    <ProjectPageLayout title={`${projectName} Inspections`} onBack={onBack}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Create Inspection</h3>

        <input
          type="date"
          value={inspectionDate}
          onChange={(event) => onDateChange(event.target.value)}
        />
        <input
          placeholder="Inspection"
          value={inspectionType}
          onChange={(event) => onTypeChange(event.target.value)}
        />
        <select
          value={inspectionStatus}
          onChange={(event) => onStatusChange(event.target.value)}
        >
          <option value="Pass">Pass</option>
          <option value="Partial Pass">Partial Pass</option>
          <option value="Fail">Fail</option>
        </select>

        <button onClick={onCreate} style={buttonStyle}>
          Save Inspection
        </button>
      </div>

      <button
        onClick={onRefresh}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        Refresh Inspections
      </button>

      <RecordTable headers={["Date", "Inspection", "Status"]}>
        {inspections.map((inspection) => (
          <tr key={inspection.id}>
            <td style={tableCellStyle}>{formatDate(inspection.date)}</td>
            <td style={tableCellStyle}>{inspection.inspection_type}</td>
            <td style={tableCellStyle}>{inspection.status}</td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default InspectionsPage;
