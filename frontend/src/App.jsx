import { useEffect, useState } from "react";
import {
  registerUser,
  loginUser,
  fetchProjects,
  createProject,
  fetchTasks,
  createTask,
  deleteTask,
  updateTask,
  fetchTemplates,
  saveTemplate,
  applyTemplate,
  exportProjectPdf,
} from "./services/api";
import GanttChart from "./components/GanttChart";

function App() {
  const [tasks, setTasks] = useState([]);
  const [editingCell, setEditingCell] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [templates, setTemplates] = useState([]);
  const [templateName, setTemplateName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState("login");

  const loadTasks = async () => {
    if (!selectedProjectId) return;
    
    const data = await fetchTasks(selectedProjectId);
    setTasks(data.tasks);
  };

  const loadProjects = async () => {
    const data = await fetchProjects();

    if (data.detail === "Not authenticated" || data.detail === "Invalid token") {
      handleLogout();
      return;
    }

    setProjects(data.projects);

    if (data.projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(data.projects[0].id);
    }
  };

  useEffect(() => {
    if (token) {
      loadProjects();
      loadTemplates();
    }
  }, [token]);

  useEffect(() => {
    if (token && selectedProjectId) {
      loadTasks();
    }
  }, [token, selectedProjectId]);
    
  const handleCellClick = (task, field) => {
    setEditingCell({ id: task.id ?? "new", field });

    if (field === "predecessor") {
      setEditValue(task.predecessor || "");
    } else if (field === "manual_start_date") {
      setEditValue(task.manual_start_date || task.start_date || "");
    } else {
      setEditValue(task[field]);
    }
  };

  const handleCellSave = async (task) => {
    if (!editingCell) return;

    let value = editValue;

    if (editingCell.field === "duration") {
      value = Number(editValue);
    }

    if (editingCell.field === "predecessor") {
      value = editValue === "" ? null : editValue;
    }

    if (task.id === null) {
      await createTask(selectedProjectId, {
        name: editingCell.field === "name" ? value : "New Task",
        duration: editingCell.field === "duration" ? value : 1,
        predecessor:
          editingCell.field === "predecessor" ? value : null,
        manual_start_date:
          editingCell.field === "manual_start_date" ? value : null,
      });
    } else {
      await updateTask(selectedProjectId, task.id, {
        ...task,
        [editingCell.field]: value,
      });
    }

    setEditingCell(null);
    loadTasks();
  };


  const handleDelete = async (id) => {
    await deleteTask(selectedProjectId, id);
    loadTasks();
  };

  const [selectedTaskId, setSelectedTaskId] = useState(null);

  const getEmptyRow = () => ({
    id: null,
    name: "",
    duration: "",
    manual_start_date: "",
    predecessor: "",
  })

  const formatDate = (date) => {
    if (!date) return "-";

    const [y, m, d] = date.split("-");
    return `${m}/${d}/${y}`;
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    const project = await createProject({
      name: newProjectName,
    });

    setNewProjectName("");
    await loadProjects();
    setSelectedProjectId(project.id);
  };

  const loadTemplates = async () => {
    const data = await fetchTemplates();

    if (data.detail === "Not authenticated" || data.detail === "Invalid token") {
      handleLogout();
      return;
    }

    setTemplates(data.templates);
  };

  const handleSaveTemplate = async () => {
    if (!selectedProjectId || !templateName.trim()) return;

    await saveTemplate(selectedProjectId, {
      name: templateName,
    });

    setTemplateName("");
    loadTemplates();
  };

  const handleApplyTemplate = async () => {
    if (!selectedProjectId || !selectedTemplateId) return;

    await applyTemplate(selectedProjectId, selectedTemplateId);
    loadTasks();
  };

  const handleRegister = async () => {
    const data = await registerUser({
      email,
      password,
    });

    if (data.id) {
      setAuthMode("login");
      setPassword("");
    }
  };

  const handleLogin = async () => {
    const data = await loginUser(email, password);

    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setEmail("");
      setPassword("");
      loadProjects();
      loadTemplates();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setProjects([]);
    setTasks([]);
    setSelectedProjectId(null);
  };

  const buttonStyle = {
    padding: "3px 12px",
    border: "1px solid #bbb",
    borderRadius: "6px",
    cursor: "pointer",
    marginLeft: "8px",
  };

  if (!token) {
    return (
      <div style={{ padding: "20px" }}>
        <h1>Construction Scheduler</h1>

        <h2>{authMode === "login" ? "Login" : "Register"}</h2>

        <input
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {authMode === "login" ? (
          <button onClick={handleLogin}>Login</button>
        ) : (
          <button onClick={handleRegister}>Register</button>
        )}

        <button
          onClick={() =>
            setAuthMode(authMode === "login" ? "register" : "login")
          }
        >
          {authMode === "login"
            ? "Need an account? Register"
            : "Already have an account? Login"}
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        fontFamily: "Arial, sans-serif",
      }}
    >
      {/* SIDEBAR */}
      <aside
        style={{
          width: "200px",
          minWidth: "200px",
          padding: "20px",
          borderRight: "1px solid #ddd",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          position: "sticky",
          top: 0,
        }}
      >
        {/* PROJECTS */}
        <div
          style={{
            padding: "15px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            marginTop: "20px",
            marginBottom: "15px",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Projects</h3>

          <select
            value={selectedProjectId || ""}
            onChange={(e) => setSelectedProjectId(Number(e.target.value))}
            style={{
              width: "100%",
              marginBottom: "8px",
            }}
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>

          <input
            placeholder="New project name"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            style={{
              width: "100%",
              marginBottom: "8px",
              boxSizing: "border-box",
            }}
          />

          <button onClick={handleCreateProject} style={buttonStyle}>
            Create Project
          </button>
        </div>

        {/* TEMPLATES */}
        <div
          style={{
            padding: "15px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            marginBottom: "15px",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Templates</h3>

          <input
            placeholder="Template name"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            style={{
              width: "100%",
              marginBottom: "8px",
              boxSizing: "border-box",
            }}
          />

          <button onClick={handleSaveTemplate} style={buttonStyle}>
            Save Template
          </button>

          <select
            value={selectedTemplateId}
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            style={{
              width: "100%",
              marginTop: "8px",
              marginBottom: "8px",
            }}
          >
            <option value="">Select template</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>

          <button onClick={handleApplyTemplate} style={buttonStyle}>
            Apply Template
          </button>
        </div>

        <button
          onClick={() => exportProjectPdf(selectedProjectId)}
          disabled={!selectedProjectId}
          style={buttonStyle}
        >
          Export Schedule as PDF
        </button>

        <div style={{ marginTop: "auto" }}>
          <button onClick={handleLogout} style={buttonStyle}>
            Logout
          </button>
        </div>

      </aside>
      
      <main>
        <h2
          style={{
            textAlign: "center",
            width: "100%",
            marginBottom: "20px",
          }}
          >
            Schedule
          </h2>

        <table
          style={{
            width: "100%",
            minWidth: "1400px",
            borderCollapse: "collapse",
            marginTop: "20px",
            tableLayout: "fixed",
          }}
        >
        <thead>
          <tr>
            <th
              style={{
                width: "50px",
                padding: "3px",
                background: "#f3f4f6",
                border: "1px solid #ddd",
                textAlign: "left",
              }}
            >
              Id
            </th>

            <th
              style={{
                padding: "10px",
                background: "#f3f4f6",
                border: "1px solid #ddd",
                textAlign: "left",
              }}
            >
              Task
            </th>

            <th style={{
              width: "95px",
              padding: "10px",
              background: "#f3f4f6",
              border: "1px solid #ddd",
              textAlign: "left",
            }}
            >
              Duration
            </th>

            <th style={{
              width: "125px",
              padding: "10px",
              background: "#f3f4f6",
              border: "1px solid #ddd",
              textAlign: "left",
            }}
            >
              Start
            </th>

            <th 
              style={{
                width: "125px",
                padding: "10px",
                background: "#f3f4f6",
                border: "1px solid #ddd",
                textAlign: "left",
              }}
            >
              End
            </th>

            <th 
            style={{
              width: "130px",
              padding: "10px",
              background: "#f3f4f6",
              border: "1px solid #ddd",
              textAlign: "left",
            }}
            >
              Predecessor
            </th>

            <th
              style={{
                padding: "10px",
                background: "#f3f4f6",
                border: "1px solid #ddd",
                textAlign: "left",
              }}
            >
              Actions
            </th>

          </tr>
        </thead>

        <tbody>
          {[...tasks, getEmptyRow()].map((task, index) => {
            const isNew = task.id === null;

            return (
            <tr 
              key={task.id ?? "new"}
              onClick={() => !isNew && setSelectedTaskId(task.id)}
              style={{
                background:
                  selectedTaskId === task.id
                    ? "#e0f2fe"
                    : index % 2 === 0
                    ? "#ffffff"
                    : "#f9fafb",
                cursor: "pointer",
              }}
            >
              <td>{isNew ? "": index + 1}</td>
              {/* TASK NAME */}
              <td
                onClick={(e) => {
                  e.stopPropagation();
                  handleCellClick(task, "name")
                }}
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                }}
              >
                {editingCell?.id === (task.id ?? "new") &&
                editingCell.field === "name" ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleCellSave(task)}
                  />
                ) : (
                  task.name
                )}
              </td>

              {/* DURATION */}
              <td
                onClick={(e) => {
                  e.stopPropagation();
                  handleCellClick(task, "duration")
                }}
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                }}
              >
                {editingCell?.id === (task.id ?? "new") &&
                editingCell.field === "duration" ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleCellSave(task)}
                  />
                ) : (
                  task.duration
                )}
              </td>

              {/* START / END */}
              <td
                onClick={(e) => {
                  e.stopPropagation();
                  handleCellClick(task, "manual_start_date");
                }}
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                }}
              >
                {editingCell?.id === (task.id ?? "new") &&
                editingCell.field === "manual_start_date" ? (
                  <input
                    autoFocus
                    type="date"
                    value={editValue || ""}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleCellSave(task)}
                  />
                ) : (
                  formatDate(task.start_date)
                )}
              </td>
              <td
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                }}
              >
                {formatDate(task.end_date)}
              </td>

              {/* PREDECESSOR */}
             <td
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCellClick(task, "predecessor");
                  }}
                  style={{
                    padding: "8px",
                    border: "1px solid #ddd",
                  }}
                >
                  {editingCell?.id === (task.id ?? "new") &&
                  editingCell.field === "predecessor" ? (
                    <input
                      autoFocus
                      placeholder="1, 1+3, 1SS, 1SS+4"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => handleCellSave(task)}
                    />
                  ) : (
                    task.predecessor || "-"
                  )}
              </td>
              {/* DELETE */}
              <td
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                }}
              >
                {!isNew && (
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(task.id);
                  }}
                  >
              
                  
                  Delete
                </button>
                )}
              </td>

            </tr>
          );
        })}
        </tbody>
      </table>
      <GanttChart tasks={tasks} selectedTaskId={selectedTaskId} />
      </main>
    </div>
  );
}

export default App;