import FormField from "../components/FormField";
import { buttonStyle } from "../styles";

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
}) {
  return (
    <div className="home-page">
      <h1>FieldFlow</h1>

      <p>Construction planning and field management</p>

      <div style={{ maxWidth: "350px", margin: "16px auto 0" }}>
        <FormField label="Project" htmlFor="project-select">
          <select
            id="project-select"
            className="field-control"
            value={selectedProjectId || ""}
            onChange={(event) => onProjectSelect(Number(event.target.value))}
          >
            <option value="">Select project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="home-card-grid">
        <div className="home-card">
          <h3>Add New Project</h3>

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

            <button
              type="submit"
              className="button-primary"
              disabled={isCreating}
              aria-busy={isCreating}
              style={buttonStyle}
            >
              {isCreating ? "Adding project…" : "Add Project"}
            </button>
          </form>
        </div>

        <div className="home-card">
          <h3>Active Projects</h3>
          <p>{projects.length} active project(s)</p>
        </div>

        <div className="home-card">
          <h3>Schedule Templates</h3>
          <p>{templates.length} saved template(s)</p>
        </div>
      </div>

      <button
        onClick={onLogout}
        style={{
          ...buttonStyle,
          marginTop: "30px",
        }}
      >
        Logout
      </button>
    </div>
  );
}

export default HomePage;
