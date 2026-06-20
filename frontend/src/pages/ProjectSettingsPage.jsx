import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordTable from "../components/RecordTable";
import { buttonStyle, tableCellStyle } from "../styles";

function ProjectSettingsPage({
  projectName,
  projectCompanies,
  companyName,
  companyTrade,
  onBack,
  onCreate,
  onNameChange,
  onTradeChange,
}) {
  return (
    <ProjectPageLayout title={`${projectName} Settings`} onBack={onBack}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Add Company</h3>

        <input
          placeholder="Company name"
          value={companyName}
          onChange={(event) => onNameChange(event.target.value)}
        />
        <input
          placeholder="Trade"
          value={companyTrade}
          onChange={(event) => onTradeChange(event.target.value)}
        />
        <button onClick={onCreate} style={buttonStyle}>
          Add Company
        </button>
      </div>

      <RecordTable headers={["Company", "Trade"]}>
        {projectCompanies.map((company) => (
          <tr key={company.id}>
            <td style={tableCellStyle}>{company.name}</td>
            <td style={tableCellStyle}>{company.trade}</td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default ProjectSettingsPage;
