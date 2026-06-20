import FormField from "../components/FormField";
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
      <form
        className="form-stack form-card"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <h3>Add Company</h3>

        <FormField label="Company name" htmlFor="project-company-name" required>
          <input
            id="project-company-name"
            className="field-control"
            autoComplete="organization"
            required
            value={companyName}
            onChange={(event) => onNameChange(event.target.value)}
          />
        </FormField>
        <FormField label="Trade" htmlFor="project-company-trade">
          <input
            id="project-company-trade"
            className="field-control"
            value={companyTrade}
            onChange={(event) => onTradeChange(event.target.value)}
          />
        </FormField>
        <button type="submit" className="button-primary" style={buttonStyle}>
          Add Company
        </button>
      </form>

      <RecordTable
        label="Project companies"
        emptyMessage="No companies yet. Add the first project company above."
        headers={["Company", "Trade"]}
      >
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
