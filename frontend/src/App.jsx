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
  fetchDailyLogs,
  createDailyLog,
} from "./services/api";
import GanttChart from "./components/GanttChart";

function App() {
  //usestates
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
  const [currentPage, setCurrentPage] = useState("home");
  const [dailyLogs, setDailyLogs] = useState([]);
  const [logDate, setLogDate] = useState("");
  const [logCompany, setLogCompany] = useState("");
  const [logManpower, setLogManpower] = useState("");
  const [logWorkPerformed, setLogWorkPerformed] = useState("");
  const [logDelays, setLogDelays] = useState("");
  const [logNotes, setLogNotes] = useState("");
  

  //project and task load
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

  //table logic  
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

  //save and load templates
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

  //authentaction
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
    marginLeft: "1px",
  };

  //Daily log logic
  const loadDailyLogs = async () => {
    if (!selectedProjectId) return;

    const data = await fetchDailyLogs(selectedProjectId);
    setDailyLogs(data.daily_logs || []);
  };

  const handleCreateDailyLog = async () => {
    if (!selectedProjectId || !logDate || !logCompany || !logManpower) return;

    await createDailyLog(selectedProjectId, {
      date: logDate,
      company: logCompany,
      manpower: Number(logManpower),
      work_performed: logWorkPerformed,
      delays: logDelays,
      notes: logNotes,
    });

    setLogDate("");
    setLogCompany("");
    setLogManpower("");
    setLogWorkPerformed("");
    setLogDelays("");
    setLogNotes("");

    loadDailyLogs();
  };

  //login page
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

  //homepage
  if (currentPage === "home") {
    return (
      <div style={{ padding: "24px", fontFamily: "Arial, sans-serif", textAlign: "center" }}>
        <h1>Construction Management Software</h1>

        <p style={{ color: "#666" }}>
          Select a project to open its dashboard.
        </p>

        <select
          value={selectedProjectId || ""}
          onChange={(e) => {
            setSelectedProjectId(Number(e.target.value));
            setCurrentPage("projectDashboard");
          }}
        >
          <option value="">Select project</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>

        <div style={{ marginTop: "20px" }}>
          <h3>Active Projects</h3>
          <p>{projects.length} active project(s)</p>

          <h3>Templates</h3>
          <p>{templates.length} saved template(s)</p>
        </div>

        <button onClick={handleLogout} style={buttonStyle}>
          Logout
        </button>
      </div>
    );
  }

  //Project Dashboard
  if (currentPage === "projectDashboard") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return (
      <div style={{ padding: "24px", fontFamily: "Arial, sans-serif", textAlign: "center" }}>
        <button onClick={() => setCurrentPage("home")} style={buttonStyle}>
          Back to Home
        </button>

        <h1>{selectedProject?.name || "Project"} Dashboard</h1>

        <div style={{ display: "flex", gap: "15px", marginTop: "20px" }}>
          <div
            style={{
              padding: "20px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              width: "250px",
            }}
          >
            <h3>Schedule</h3>
            <p>Open this project’s schedule.</p>

            <button
              onClick={() => setCurrentPage("scheduler")}
              style={buttonStyle}
            >
              Open Schedule
            </button>
          </div>
        <div
          style={{
            padding: "20px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            width: "250px",
          }}
        >
          <h3>Daily Logs</h3>
          <p>Track manpower, work performed, delays, and site notes.</p>

          <button
            onClick={() => setCurrentPage("dailyLogs")}
            style={buttonStyle}
          >
            Open Daily Logs
          </button>
        </div>
        </div>
      </div>
    );
  }

  //Daily log page
  if (currentPage === "dailyLogs") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return (
      <div style={{ padding: "24px", fontFamily: "Arial, sans-serif" }}>
        <button
          onClick={() => setCurrentPage("projectDashboard")}
          style={buttonStyle}
        >
          Back to Project Dashboard
        </button>

        <h1>{selectedProject?.name || "Project"} Daily Logs</h1>

        <div style={{ border: "1px solid #ddd", padding: "15px", borderRadius: "8px" }}>
          <h3>Create Daily Log</h3>

          <input type="date" value={logDate} onChange={(e) => setLogDate(e.target.value)} />
          <input placeholder="Company" value={logCompany} onChange={(e) => setLogCompany(e.target.value)} />
          <input placeholder="Manpower" value={logManpower} onChange={(e) => setLogManpower(e.target.value)} />

          <textarea placeholder="Work performed" value={logWorkPerformed} onChange={(e) => setLogWorkPerformed(e.target.value)} />
          <textarea placeholder="Delays / Issues" value={logDelays} onChange={(e) => setLogDelays(e.target.value)} />
          <textarea placeholder="Notes" value={logNotes} onChange={(e) => setLogNotes(e.target.value)} />

          <button onClick={handleCreateDailyLog} style={buttonStyle}>
            Save Daily Log
          </button>
        </div>

        <button onClick={loadDailyLogs} style={{ ...buttonStyle, marginTop: "15px" }}>
          Refresh Logs
        </button>

        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "20px" }}>
          <thead>
            <tr>
              {["Date", "Company", "Manpower", "Work Performed", "Delays", "Notes"].map((header) => (
                <th
                  key={header}
                  style={{
                    padding: "10px",
                    background: "#f3f4f6",
                    border: "1px solid #ddd",
                    textAlign: "left",
                  }}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {dailyLogs.map((log) => (
              <tr key={log.id}>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{formatDate(log.date)}</td>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{log.company}</td>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{log.manpower}</td>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{log.work_performed}</td>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{log.delays}</td>
                <td style={{ padding: "8px", border: "1px solid #ddd" }}>{log.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  //scheduling page sidebar
  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        fontFamily: "Arial, sans-serif",
      }}
    >
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
        <button
          onClick={() => setCurrentPage("projectDashboard")}
          style={buttonStyle}
        >
          Project Dashboard
        </button>

        {/* Template creation and selection */}
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
        
        {/* Export schedule as PDF */}
        <button
          onClick={() => exportProjectPdf(selectedProjectId)}
          disabled={!selectedProjectId}
          style={buttonStyle}
        >
          Export Schedule as PDF
        </button>

        {/* Logout */}
        <div style={{ marginTop: "auto" }}>
          <button onClick={handleLogout} style={buttonStyle}>
            Logout
          </button>
        </div>

      </aside>
      
      {/* Main content of scheduling page */}
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

        {/* Scheduling table */}
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
            {/* Column Names and styles */}
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
          {/* Populate new empty row */}
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

              {/* Task Name */}

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

              {/* Duration */}

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

              {/* Start and End Dates */}

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

              {/* Predecessor */}

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

              {/* Delete */}

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

      {/* Gantt Chart */}
      
      <GanttChart tasks={tasks} selectedTaskId={selectedTaskId} />

      </main>
    </div>
  );
}

export default App;