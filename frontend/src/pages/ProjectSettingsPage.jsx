import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordTable from "../components/RecordTable";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";

function ProjectSettingsPage({
  projectName,
  projectCompanies,
  companyName,
  companyTrade,
  onNavigate,
  onLogout,
  onCreate,
  onNameChange,
  onTradeChange,
  isCreating = false,
  isLoading = false,
}) {
  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectSettings"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader title="Project Settings" />

      <Card
        as="form"
        title="Add Company"
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
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
        <Button
          type="submit"
          variant="primary"
          disabled={isCreating}
          aria-busy={isCreating}
        >
          {isCreating ? "Adding company…" : "Add Company"}
        </Button>
      </Card>

      <RecordTable
        label="Project companies"
        isLoading={isLoading}
        loadingMessage="Loading project companies…"
        emptyMessage="No companies yet. Add the first project company above."
        headers={["Company", "Trade"]}
      >
        {projectCompanies.map((company) => (
          <tr key={company.id}>
            <RecordCell label="Company">{company.name}</RecordCell>
            <RecordCell label="Trade">{company.trade}</RecordCell>
          </tr>
        ))}
      </RecordTable>
    </ProjectLayout>
  );
}

export default ProjectSettingsPage;
