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
}) {
  return (
    <div className="home-page">
      <h1>Construction Management Software</h1>

      <p style={{ color: "#666" }}>
        Select a Community to open its dashboard.
      </p>

      <div style={{ maxWidth: "350px", margin: "16px auto 0" }}>
        <FormField label="Community" htmlFor="project-select">
          <select
            id="project-select"
            className="field-control"
            value={selectedProjectId || ""}
            onChange={(event) => onProjectSelect(Number(event.target.value))}
          >
            <option value="">Select community</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="home-card-grid">
        <div
          className="home-card"
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
          }}
        >
          <h3>Add New Community</h3>

          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault();
              onCreateProject();
            }}
          >
            <FormField label="Community name" htmlFor="community-name" required>
              <input
                id="community-name"
                className="field-control"
                autoComplete="organization"
                required
                value={newProjectName}
                onChange={(event) =>
                  onNewProjectNameChange(event.target.value)
                }
              />
            </FormField>

            <button type="submit" style={buttonStyle}>
              Add Community
            </button>
          </form>
        </div>

        <div
          className="home-card"
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
          }}
        >
          <h3>Active Communities</h3>
          <p>{projects.length} active project(s)</p>
        </div>

        <div
          className="home-card"
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
          }}
        >
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
