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
    <div
      style={{
        padding: "24px",
        fontFamily: "Arial, sans-serif",
        textAlign: "center",
      }}
    >
      <h1>Construction Management Software</h1>

      <p style={{ color: "#666" }}>
        Select a Community to open its dashboard.
      </p>

      <select
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

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "20px",
          flexWrap: "wrap",
          marginTop: "20px",
        }}
      >
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
            width: "350px",
          }}
        >
          <h3>Add New Community</h3>

          <input
            placeholder="Community Name"
            value={newProjectName}
            onChange={(event) =>
              onNewProjectNameChange(event.target.value)
            }
            style={{
              width: "100%",
              marginBottom: "10px",
              padding: "8px",
              boxSizing: "border-box",
            }}
          />

          <button onClick={onCreateProject} style={buttonStyle}>
            Add Community
          </button>
        </div>

        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
            width: "350px",
          }}
        >
          <h3>Active Communities</h3>
          <p>{projects.length} active project(s)</p>
        </div>

        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
            width: "350px",
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
