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
    setProjects(data.projects);

    if (data.projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(data.projects[0].id);
    }
  };

  useEffect(() => {
    loadProjects();
    loadTemplates();
  }, []);

  useEffect(() => {
    loadTasks();
  }, [selectedProjectId]);
    
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
    <div style={{ padding: "20px" }}>
      <h1>Scheduler App</h1>
      <button
        onClick={handleLogout}
        style={{ marginBottom: "15px" }}
      >
        Logout
      </button>

      <div style={{ marginBottom: "15px" }}>
        <input
          placeholder="Template name"
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
        />

        <button onClick={handleSaveTemplate}>
          Save Template
        </button>

        <select
          value={selectedTemplateId}
          onChange={(e) => setSelectedTemplateId(e.target.value)}
          style={{ marginLeft: "10px" }}
        >
          <option value="">Select template</option>
          {templates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
            </option>
          ))}
        </select>

        <button onClick={handleApplyTemplate}>
          Apply Template
        </button>
      </div>

      <div style={{ marginBottom: "15px" }}>
        <select
          value={selectedProjectId || ""}
          onChange={(e) => setSelectedProjectId(Number(e.target.value))}
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
          style={{ marginLeft: "10px" }}
        />

        <button onClick={handleCreateProject}>
          Create Project
        </button>
      </div>

      {/* TASK TABLE */}
      <table border="1" cellPadding="5" style={{ marginTop: "20px" }}>
        <thead>
          <tr>
            <th>Index</th>
            <th>Task</th>
            <th>Duration</th>
            <th>Start</th>
            <th>End</th>
            <th>Predecessor</th>
            <th>Actions</th>
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
                  selectedTaskId === task.id ? "#d3e5ff" : "transparent",
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
                style={{ cursor: "pointer" }}
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
                style={{ cursor: "pointer" }}
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
                style={{ cursor: "pointer" }}
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
              <td>{formatDate(task.end_date)}</td>

              {/* PREDECESSOR */}
             <td
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCellClick(task, "predecessor");
                  }}
                  style={{ cursor: "pointer" }}
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
              <td>
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
      <button
        onClick={() => exportProjectPdf(selectedProjectId)}
        disabled={!selectedProjectId}
        style={{ marginLeft: "10px" }}
      >
        Export PDF
      </button>
      <GanttChart tasks={tasks} selectedTaskId={selectedTaskId} />
      
    </div>
  );
}

export default App;