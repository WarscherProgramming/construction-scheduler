import FormField from "../components/FormField";
import LoadingState from "../components/LoadingState";
import SkipLink from "../components/SkipLink";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";

function HomePage({
  projects,
  templates,
  selectedProjectId,
  newProjectName,
  onProjectSelect,
  onNewProjectNameChange,
  onCreateProject,
  onLogout,
  isCreating = false,
  isLoadingProjects = false,
  isLoadingTemplates = false,
}) {
  return (
    <>
      <SkipLink />
      <main id="main-content" className="home-page" tabIndex={-1}>
        <PageHeader
          title="FieldFlow"
          subtitle="Construction planning and field management"
          actions={
            <Button onClick={onLogout}>
              <Icon name="log-out" size={17} />
              Logout
            </Button>
          }
        />

        <div style={{ maxWidth: "350px" }}>
          <FormField label="Project" htmlFor="project-select">
            <select
              id="project-select"
              className="field-control"
              disabled={isLoadingProjects}
              value={selectedProjectId || ""}
              onChange={(event) => onProjectSelect(Number(event.target.value))}
            >
              <option value="">
                {isLoadingProjects ? "Loading projects…" : "Select project"}
              </option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        <div className="home-card-grid">
          <Card title="Add New Project">
            <form
              className="form-stack"
              onSubmit={(event) => {
                event.preventDefault();
                onCreateProject();
              }}
            >
              <FormField label="Project name" htmlFor="project-name" required>
                <input
                  id="project-name"
                  className="field-control"
                  autoComplete="organization"
                  required
                  value={newProjectName}
                  onChange={(event) =>
                    onNewProjectNameChange(event.target.value)
                  }
                />
              </FormField>

              <Button
                type="submit"
                variant="primary"
                disabled={isCreating}
                aria-busy={isCreating}
              >
                <Icon name="plus" size={17} />
                {isCreating ? "Adding project…" : "Add Project"}
              </Button>
            </form>
          </Card>

          <Card title="Active Projects">
            {isLoadingProjects ? (
              <LoadingState message="Loading projects…" />
            ) : (
              <p>{projects.length} active project(s)</p>
            )}
          </Card>

          <Card title="Schedule Templates">
            {isLoadingTemplates ? (
              <LoadingState message="Loading templates…" />
            ) : (
              <p>{templates.length} saved template(s)</p>
            )}
          </Card>
        </div>
      </main>
    </>
  );
}

export default HomePage;
