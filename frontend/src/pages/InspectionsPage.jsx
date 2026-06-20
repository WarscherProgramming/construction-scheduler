import FormField from "../components/FormField";
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
        <h3>Create Inspection</h3>

        <FormField label="Date" htmlFor="inspection-date" required>
          <input
            id="inspection-date"
            className="field-control"
            type="date"
            required
            value={inspectionDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>
        <FormField label="Inspection" htmlFor="inspection-type" required>
          <input
            id="inspection-type"
            className="field-control"
            required
            value={inspectionType}
            onChange={(event) => onTypeChange(event.target.value)}
          />
        </FormField>
        <FormField label="Status" htmlFor="inspection-status">
          <select
            id="inspection-status"
            className="field-control"
            value={inspectionStatus}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            <option value="Pending">Pending</option>
            <option value="Pass">Pass</option>
            <option value="Partial Pass">Partial Pass</option>
            <option value="Fail">Fail</option>
          </select>
        </FormField>

        <button type="submit" style={buttonStyle}>
          Save Inspection
        </button>
      </form>

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
