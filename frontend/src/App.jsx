import { useCallback, useEffect, useRef, useState } from "react";
import {
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
  fetchInspections,
  createInspection,
  fetchNotesDelays,
  createNoteDelay,
  fetchChangeOrders,
  createChangeOrder,
  fetchProjectCompanies,
  createProjectCompany,
  deleteChangeOrder,
  reorderTasks,
} from "./services/api";
import { ApiError } from "./services/httpClient";
import { arrayMove } from "@dnd-kit/sortable";

import { useAuth } from "./auth/authContext";
import AuthPage from "./pages/AuthPage";
import ChangeOrdersPage from "./pages/ChangeOrdersPage";
import FeedbackBanner from "./components/FeedbackBanner";
import DailyLogsPage from "./pages/DailyLogsPage";
import HomePage from "./pages/HomePage";
import InspectionsPage from "./pages/InspectionsPage";
import NotesDelaysPage from "./pages/NotesDelaysPage";
import ProjectDashboardPage from "./pages/ProjectDashboardPage";
import ProjectSettingsPage from "./pages/ProjectSettingsPage";
import SchedulerPage from "./pages/SchedulerPage";
function App() {
  const { isAuthenticated, login, logout, register } = useAuth();

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [currentPage, setCurrentPage] = useState("home");
  const [dailyLogs, setDailyLogs] = useState([]);
  const [logDate, setLogDate] = useState("");
  const [logCompany, setLogCompany] = useState("");
  const [logManpower, setLogManpower] = useState("");
  const [logNotes, setLogNotes] = useState("");
  const [inspections, setInspections] = useState([]);
  const [inspectionDate, setInspectionDate] = useState("");
  const [inspectionType, setInspectionType] = useState("");
  const [inspectionStatus, setInspectionStatus] = useState("Pending");
  const [notesDelays, setNotesDelays] = useState([]);
  const [noteDelayDate, setNoteDelayDate] = useState("");
  const [noteDelayType, setNoteDelayType] = useState("Note");
  const [noteDelayCompany, setNoteDelayCompany] = useState("");
  const [noteDelayDescription, setNoteDelayDescription] = useState("");
  const [noteDelayImpact, setNoteDelayImpact] = useState("");
  const [changeOrders, setChangeOrders] = useState([]);
  const [changeOrderDate, setChangeOrderDate] = useState("");
  const [changeOrderNumber, setChangeOrderNumber] = useState("");
  const [changeOrderCompany, setChangeOrderCompany] = useState("");
  const [changeOrderStatus, setChangeOrderStatus] = useState("Pending");
  const [changeOrderDescription, setChangeOrderDescription] = useState("");
  const [changeOrderAmount, setChangeOrderAmount] = useState("");
  const [changeOrderResponsibleParty, setChangeOrderResponsibleParty] = useState("");
  const [projectCompanies, setProjectCompanies] = useState([]);
  const [companyName, setCompanyName] = useState("");
  const [companyTrade, setCompanyTrade] = useState("");
  const [scheduleView, setScheduleView] = useState("table");
  const [notice, setNotice] = useState(null);
  const selectedProjectIdRef = useRef(selectedProjectId);

  useEffect(() => {
    selectedProjectIdRef.current = selectedProjectId;
  }, [selectedProjectId]);

  const selectProject = useCallback((projectId) => {
    selectedProjectIdRef.current = projectId;
    setSelectedProjectId(projectId);
  }, []);

  const resetApplicationState = useCallback(() => {
    selectedProjectIdRef.current = null;
    setProjects([]);
    setTasks([]);
    setTemplates([]);
    setDailyLogs([]);
    setInspections([]);
    setNotesDelays([]);
    setChangeOrders([]);
    setProjectCompanies([]);
    setSelectedProjectId(null);
    setCurrentPage("home");
  }, []);

  const handleLogout = useCallback(() => {
    logout();
    resetApplicationState();
    setNotice(null);
  }, [logout, resetApplicationState]);

  const showNotice = useCallback((type, message) => {
    setNotice({
      id: Date.now(),
      type,
      message,
    });
  }, []);

  const reportRequestError = useCallback((context, error) => {
    const message =
      error instanceof ApiError ? error.message : "Unexpected application error";

    console.error(`${context}: ${message}`, error);
    showNotice("error", `${context}. ${message}`);
  }, [showNotice]);

  const reportValidationError = useCallback((message) => {
    showNotice("error", message);
  }, [showNotice]);

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data.projects);
      selectProject(
        selectedProjectIdRef.current ?? data.projects[0]?.id ?? null
      );
    } catch (error) {
      reportRequestError("Unable to load projects", error);
    }
  }, [reportRequestError, selectProject]);

  const loadTemplates = useCallback(async () => {
    try {
      const data = await fetchTemplates();
      setTemplates(data.templates);
    } catch (error) {
      reportRequestError("Unable to load templates", error);
    }
  }, [reportRequestError]);

  const loadTasks = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchTasks(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setTasks(data.tasks);
      }
    } catch (error) {
      reportRequestError("Unable to load tasks", error);
    }
  }, [reportRequestError, selectedProjectId]);

  const loadDailyLogs = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchDailyLogs(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setDailyLogs(data.daily_logs || []);
      }
    } catch (error) {
      reportRequestError("Unable to load daily logs", error);
    }
  }, [reportRequestError, selectedProjectId]);

  const loadInspections = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchInspections(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setInspections(data.inspections || []);
      }
    } catch (error) {
      reportRequestError("Unable to load inspections", error);
    }
  }, [reportRequestError, selectedProjectId]);

  const loadNotesDelays = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchNotesDelays(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setNotesDelays(data.notes_delays || []);
      }
    } catch (error) {
      reportRequestError("Unable to load notes and delays", error);
    }
  }, [reportRequestError, selectedProjectId]);

  const loadChangeOrders = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchChangeOrders(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setChangeOrders(data.change_orders || []);
      }
    } catch (error) {
      reportRequestError("Unable to load change orders", error);
    }
  }, [reportRequestError, selectedProjectId]);

  const loadProjectCompanies = useCallback(async () => {
    const projectId = selectedProjectId;
    if (!projectId) return;

    try {
      const data = await fetchProjectCompanies(projectId);

      if (selectedProjectIdRef.current === projectId) {
        setProjectCompanies(data.companies || []);
      }
    } catch (error) {
      reportRequestError("Unable to load project companies", error);
    }
  }, [reportRequestError, selectedProjectId]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const timeoutId = window.setTimeout(() => {
      void Promise.all([loadProjects(), loadTemplates()]);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [isAuthenticated, loadProjects, loadTemplates]);

  useEffect(() => {
    if (!isAuthenticated || !selectedProjectId) return;

    const timeoutId = window.setTimeout(() => {
      setTasks([]);
      setDailyLogs([]);
      setInspections([]);
      setNotesDelays([]);
      setChangeOrders([]);
      setProjectCompanies([]);

      void Promise.all([loadTasks(), loadProjectCompanies()]);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [
    isAuthenticated,
    loadProjectCompanies,
    loadTasks,
    selectedProjectId,
  ]);

  useEffect(() => {
    if (!isAuthenticated || !selectedProjectId) return;

    const pageLoaders = {
      projectDashboard: [loadChangeOrders, loadNotesDelays],
      dailyLogs: [loadDailyLogs],
      inspections: [loadInspections],
      notesDelays: [loadNotesDelays],
      changeOrders: [loadChangeOrders],
      projectSettings: [loadProjectCompanies],
    };

    const loaders = pageLoaders[currentPage] || [];
    const timeoutId = window.setTimeout(() => {
      void Promise.all(loaders.map((load) => load()));
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [
    currentPage,
    isAuthenticated,
    loadChangeOrders,
    loadDailyLogs,
    loadInspections,
    loadNotesDelays,
    loadProjectCompanies,
    selectedProjectId,
  ]);

  useEffect(() => {
    if (isAuthenticated) return;

    const timeoutId = window.setTimeout(resetApplicationState, 0);
    return () => window.clearTimeout(timeoutId);
  }, [isAuthenticated, resetApplicationState]);

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

    if (
      task.id === null &&
      editingCell.field === "name" &&
      !String(value).trim()
    ) {
      reportValidationError("Enter a task name before adding the task.");
      return;
    }

    try {
      const data =
        task.id === null
          ? await createTask(selectedProjectId, {
              name: editingCell.field === "name" ? value : "New Task",
              duration: editingCell.field === "duration" ? value : 1,
              predecessor:
                editingCell.field === "predecessor" ? value : null,
              manual_start_date:
                editingCell.field === "manual_start_date" ? value : null,
            })
          : await updateTask(selectedProjectId, task.id, {
              ...task,
              [editingCell.field]: value,
            });

      setTasks(data.tasks);
      setEditingCell(null);
    } catch (error) {
      reportRequestError("Unable to save task", error);
    }
  };

  const handleCellCancel = () => {
    setEditingCell(null);
    setEditValue("");
  };


  const handleDelete = async (id) => {
    if (!window.confirm("Delete this task? This action cannot be undone.")) {
      return;
    }

    try {
      const data = await deleteTask(selectedProjectId, id);
      setTasks(data.tasks);
      showNotice("success", "Task deleted.");
    } catch (error) {
      reportRequestError("Unable to delete task", error);
    }
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
    if (!newProjectName.trim()) {
      reportValidationError("Enter a project name before adding it.");
      return;
    }

    try {
      const project = await createProject({
        name: newProjectName,
      });

      setProjects((currentProjects) => [...currentProjects, project]);
      setNewProjectName("");
      selectProject(project.id);
      showNotice("success", `${project.name} was added.`);
    } catch (error) {
      reportRequestError("Unable to create project", error);
    }
  };

  const handleSaveTemplate = async () => {
    if (!selectedProjectId) {
      reportValidationError("Select a project before saving a template.");
      return;
    }

    if (!templateName.trim()) {
      reportValidationError("Enter a template name before saving.");
      return;
    }

    try {
      const template = await saveTemplate(selectedProjectId, {
        name: templateName,
      });

      setTemplates((currentTemplates) => [...currentTemplates, template]);
      setTemplateName("");
      showNotice("success", "Schedule template saved.");
    } catch (error) {
      reportRequestError("Unable to save template", error);
    }
  };

  const handleApplyTemplate = async () => {
    if (!selectedProjectId || !selectedTemplateId) {
      reportValidationError("Select a template before applying it.");
      return;
    }

    try {
      await applyTemplate(selectedProjectId, selectedTemplateId);
      await loadTasks();
      showNotice("success", "Schedule template applied.");
    } catch (error) {
      reportRequestError("Unable to apply template", error);
    }
  };

  //authentaction
  const handleRegister = async () => {
    try {
      await register({
        email,
        password,
      });
      setAuthMode("login");
      setPassword("");
      showNotice("success", "Account created. Log in to continue.");
    } catch (error) {
      reportRequestError("Unable to register", error);
    }
  };

  const handleLogin = async () => {
    try {
      await login(email, password);
      setEmail("");
      setPassword("");
    } catch (error) {
      reportRequestError("Unable to log in", error);
    }
  };

  const handleExportProjectPdf = async () => {
    if (!selectedProjectId) {
      reportValidationError("Select a project before exporting.");
      return;
    }

    try {
      await exportProjectPdf(selectedProjectId);
      showNotice("success", "Schedule PDF downloaded.");
    } catch (error) {
      reportRequestError("Unable to export project PDF", error);
    }
  };

  const handleCreateDailyLog = async () => {
    if (!logDate || !logCompany || !logManpower) {
      reportValidationError(
        "Complete the date, company, and manpower fields before saving."
      );
      return;
    }

    try {
      await createDailyLog(selectedProjectId, {
        date: logDate,
        company: logCompany,
        manpower: Number(logManpower),
        notes: logNotes,
      });

      setLogDate("");
      setLogCompany("");
      setLogManpower("");
      setLogNotes("");
      await loadDailyLogs();
      showNotice("success", "Daily log saved.");
    } catch (error) {
      reportRequestError("Unable to create daily log", error);
    }
  };

  const handleCreateInspection = async () => {
    if (!inspectionDate || !inspectionType) {
      reportValidationError(
        "Complete the date and inspection fields before saving."
      );
      return;
    }

    try {
      await createInspection(selectedProjectId, {
        date: inspectionDate,
        inspection_type: inspectionType,
        status: inspectionStatus,
      });

      setInspectionDate("");
      setInspectionType("");
      setInspectionStatus("Pending");
      await loadInspections();
      showNotice("success", "Inspection saved.");
    } catch (error) {
      reportRequestError("Unable to create inspection", error);
    }
  };

  const handleCreateNoteDelay = async () => {
    if (!noteDelayDate || !noteDelayDescription.trim()) {
      reportValidationError(
        "Complete the date and description fields before saving."
      );
      return;
    }

    try {
      await createNoteDelay(selectedProjectId, {
        date: noteDelayDate,
        entry_type: noteDelayType,
        company: noteDelayCompany,
        description: noteDelayDescription,
        impact: noteDelayImpact,
      });

      setNoteDelayDate("");
      setNoteDelayType("Note");
      setNoteDelayCompany("");
      setNoteDelayDescription("");
      setNoteDelayImpact("");
      await loadNotesDelays();
      showNotice(
        "success",
        noteDelayType === "Delay" ? "Delay recorded." : "Note saved."
      );
    } catch (error) {
      reportRequestError("Unable to create note or delay", error);
    }
  };

  const handleCreateChangeOrder = async () => {
    if (!changeOrderDate || !changeOrderNumber.trim()) {
      reportValidationError(
        "Complete the date and change order number before saving."
      );
      return;
    }

    try {
      await createChangeOrder(selectedProjectId, {
        date: changeOrderDate,
        co_number: changeOrderNumber,
        company: changeOrderCompany,
        status: changeOrderStatus,
        description: changeOrderDescription,
        amount: changeOrderAmount,
        responsible_party: changeOrderResponsibleParty,
      });

      setChangeOrderDate("");
      setChangeOrderNumber("");
      setChangeOrderCompany("");
      setChangeOrderStatus("Pending");
      setChangeOrderDescription("");
      setChangeOrderAmount("");
      setChangeOrderResponsibleParty("");
      await loadChangeOrders();
      showNotice("success", "Change order saved.");
    } catch (error) {
      reportRequestError("Unable to create change order", error);
    }
  };

  const handleDeleteChangeOrder = async (id) => {
    if (
      !window.confirm(
        "Delete this change order? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      await deleteChangeOrder(selectedProjectId, id);
      await loadChangeOrders();
      showNotice("success", "Change order deleted.");
    } catch (error) {
      reportRequestError("Unable to delete change order", error);
    }
  };

  //Dashboard pull task current week
  const getTasksThisWeek = () => {
    const today = new Date();

    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());

    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);

    return tasks.filter((task) => {
      if (!task.start_date) return false;

      const taskStart = new Date(task.start_date);

      return taskStart >= startOfWeek && taskStart <= endOfWeek;
    });
  };

  //project delay table
  const getProjectDelays = () => {
    return notesDelays.filter(
      (entry) => entry.entry_type === "Delay"
    );
  };

  const handleCreateProjectCompany = async () => {
    if (!companyName.trim()) {
      reportValidationError("Enter a company name before adding it.");
      return;
    }

    try {
      await createProjectCompany(selectedProjectId, {
        name: companyName,
        trade: companyTrade,
      });

      setCompanyName("");
      setCompanyTrade("");
      await loadProjectCompanies();
      showNotice("success", "Company added to the project.");
    } catch (error) {
      reportRequestError("Unable to add project company", error);
    }
  };

  //Change order totals
  const getChangeOrderTotalsByCompany = () => {
    const totals = {};

    changeOrders.forEach((co) => {
      const company = co.company || "Unassigned";

      const amount = Number(
        String(co.amount || "0").replace(/[$,]/g, "")
      );

      totals[company] = (totals[company] || 0) + amount;
    });

    return Object.entries(totals).map(([company, total]) => ({
      company,
      total,
    }));
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;

    if (!over || active.id === over.id) return;

    const oldIndex = tasks.findIndex((task) => task.id === active.id);
    const newIndex = tasks.findIndex((task) => task.id === over.id);

    const reorderedTasks = arrayMove(tasks, oldIndex, newIndex);

    setTasks(reorderedTasks);

    try {
      await reorderTasks(
        selectedProjectId,
        reorderedTasks.map((task) => task.id)
      );
    } catch (error) {
      setTasks(tasks);
      reportRequestError("Unable to reorder tasks", error);
    }
  };

  const handleToggleCollapse = async (task) => {
    const updatedTask = {
      ...task,
      is_collapsed: task.is_collapsed ? 0 : 1,
    };

    try {
      const data = await updateTask(selectedProjectId, task.id, updatedTask);
      setTasks(data.tasks);
    } catch (error) {
      reportRequestError("Unable to update task visibility", error);
    }
  };

  const taskMap = new Map(tasks.map((task) => [task.id, task]));

  const getTaskDepth = (task) => {
    let depth = 0;
    let parentId = task.parent_task_id;
    const visited = new Set();

    while (parentId && !visited.has(parentId)) {
      visited.add(parentId);
      const parent = taskMap.get(parentId);
      if (!parent) break;

      depth += 1;
      parentId = parent.parent_task_id;
    }

    return depth;
  };

  const taskHasChildren = (taskId) =>
    tasks.some((task) => task.parent_task_id === taskId);

  const isTaskHiddenByCollapsedParent = (task) => {
    let parentId = task.parent_task_id;
    const visited = new Set();

    while (parentId && !visited.has(parentId)) {
      visited.add(parentId);
      const parent = taskMap.get(parentId);
      if (!parent) break;
      if (parent.is_collapsed) return true;
      parentId = parent.parent_task_id;
    }

    return false;
  };

  const handleIndentTask = async (task) => {
    const taskIndex = tasks.findIndex((candidate) => candidate.id === task.id);
    if (taskIndex <= 0) return;

    const parent = tasks[taskIndex - 1];

    try {
      const data = await updateTask(selectedProjectId, task.id, {
        parent_task_id: parent.id,
      });
      setTasks(data.tasks);
    } catch (error) {
      reportRequestError("Unable to indent task", error);
    }
  };

  const handleOutdentTask = async (task) => {
    if (!task.parent_task_id) return;

    const parent = taskMap.get(task.parent_task_id);

    try {
      const data = await updateTask(selectedProjectId, task.id, {
        parent_task_id: parent?.parent_task_id || null,
      });
      setTasks(data.tasks);
    } catch (error) {
      reportRequestError("Unable to outdent task", error);
    }
  };

  const renderWithFeedback = (content) => (
    <>
      <FeedbackBanner
        notice={notice}
        onDismiss={() => setNotice(null)}
      />
      {content}
    </>
  );

  if (!isAuthenticated) {
    return renderWithFeedback(
      <AuthPage
        authMode={authMode}
        email={email}
        password={password}
        onEmailChange={setEmail}
        onPasswordChange={setPassword}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onToggleMode={() =>
          setAuthMode(authMode === "login" ? "register" : "login")
        }
      />
    );
  }

  if (currentPage === "home") {
    return renderWithFeedback(
      <HomePage
        projects={projects}
        templates={templates}
        selectedProjectId={selectedProjectId}
        newProjectName={newProjectName}
        onProjectSelect={(projectId) => {
          selectProject(projectId);
          setCurrentPage("projectDashboard");
        }}
        onNewProjectNameChange={setNewProjectName}
        onCreateProject={handleCreateProject}
        onLogout={handleLogout}
      />
    );
  }

  if (currentPage === "projectDashboard") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <ProjectDashboardPage
        projectName={selectedProject?.name || "Project"}
        tasksThisWeek={getTasksThisWeek()}
        changeOrderTotals={getChangeOrderTotalsByCompany()}
        projectDelays={getProjectDelays()}
        formatDate={formatDate}
        onNavigate={setCurrentPage}
      />
    );
  }

  if (currentPage === "dailyLogs") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <DailyLogsPage
        projectName={selectedProject?.name || "Project"}
        dailyLogs={dailyLogs}
        projectCompanies={projectCompanies}
        logDate={logDate}
        logCompany={logCompany}
        logManpower={logManpower}
        logNotes={logNotes}
        formatDate={formatDate}
        onBack={() => setCurrentPage("projectDashboard")}
        onRefresh={loadDailyLogs}
        onCreate={handleCreateDailyLog}
        onDateChange={setLogDate}
        onCompanyChange={setLogCompany}
        onManpowerChange={setLogManpower}
        onNotesChange={setLogNotes}
      />
    );
  }

  if (currentPage === "inspections") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <InspectionsPage
        projectName={selectedProject?.name || "Project"}
        inspections={inspections}
        inspectionDate={inspectionDate}
        inspectionType={inspectionType}
        inspectionStatus={inspectionStatus}
        formatDate={formatDate}
        onBack={() => setCurrentPage("projectDashboard")}
        onRefresh={loadInspections}
        onCreate={handleCreateInspection}
        onDateChange={setInspectionDate}
        onTypeChange={setInspectionType}
        onStatusChange={setInspectionStatus}
      />
    );
  }

  if (currentPage === "notesDelays") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <NotesDelaysPage
        projectName={selectedProject?.name || "Project"}
        notesDelays={notesDelays}
        projectCompanies={projectCompanies}
        noteDelayDate={noteDelayDate}
        noteDelayType={noteDelayType}
        noteDelayCompany={noteDelayCompany}
        noteDelayDescription={noteDelayDescription}
        noteDelayImpact={noteDelayImpact}
        formatDate={formatDate}
        onBack={() => setCurrentPage("projectDashboard")}
        onRefresh={loadNotesDelays}
        onCreate={handleCreateNoteDelay}
        onDateChange={setNoteDelayDate}
        onTypeChange={setNoteDelayType}
        onCompanyChange={setNoteDelayCompany}
        onDescriptionChange={setNoteDelayDescription}
        onImpactChange={setNoteDelayImpact}
      />
    );
  }

  if (currentPage === "changeOrders") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <ChangeOrdersPage
        projectName={selectedProject?.name || "Project"}
        changeOrders={changeOrders}
        projectCompanies={projectCompanies}
        changeOrderDate={changeOrderDate}
        changeOrderNumber={changeOrderNumber}
        changeOrderCompany={changeOrderCompany}
        changeOrderStatus={changeOrderStatus}
        changeOrderDescription={changeOrderDescription}
        changeOrderAmount={changeOrderAmount}
        changeOrderResponsibleParty={changeOrderResponsibleParty}
        formatDate={formatDate}
        onBack={() => setCurrentPage("projectDashboard")}
        onRefresh={loadChangeOrders}
        onCreate={handleCreateChangeOrder}
        onDelete={handleDeleteChangeOrder}
        onDateChange={setChangeOrderDate}
        onNumberChange={setChangeOrderNumber}
        onCompanyChange={setChangeOrderCompany}
        onStatusChange={setChangeOrderStatus}
        onDescriptionChange={setChangeOrderDescription}
        onAmountChange={setChangeOrderAmount}
        onResponsiblePartyChange={setChangeOrderResponsibleParty}
      />
    );
  }

  if (currentPage === "projectSettings") {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    return renderWithFeedback(
      <ProjectSettingsPage
        projectName={selectedProject?.name || "Project"}
        projectCompanies={projectCompanies}
        companyName={companyName}
        companyTrade={companyTrade}
        onBack={() => setCurrentPage("projectDashboard")}
        onCreate={handleCreateProjectCompany}
        onNameChange={setCompanyName}
        onTradeChange={setCompanyTrade}
      />
    );
  }

  return renderWithFeedback(
    <SchedulerPage
      tasks={tasks}
      templates={templates}
      selectedProjectId={selectedProjectId}
      selectedTaskId={selectedTaskId}
      editingCell={editingCell}
      editValue={editValue}
      templateName={templateName}
      selectedTemplateId={selectedTemplateId}
      scheduleView={scheduleView}
      setSelectedTaskId={setSelectedTaskId}
      setEditValue={setEditValue}
      setTemplateName={setTemplateName}
      setSelectedTemplateId={setSelectedTemplateId}
      setScheduleView={setScheduleView}
      onNavigate={setCurrentPage}
      onSaveTemplate={handleSaveTemplate}
      onApplyTemplate={handleApplyTemplate}
      onExport={handleExportProjectPdf}
      onLogout={handleLogout}
      onDragEnd={handleDragEnd}
      onCellClick={handleCellClick}
      onCellSave={handleCellSave}
      onCellCancel={handleCellCancel}
      onDelete={handleDelete}
      onIndent={handleIndentTask}
      onOutdent={handleOutdentTask}
      onToggleCollapse={handleToggleCollapse}
      getEmptyRow={getEmptyRow}
      formatDate={formatDate}
      taskHasChildren={taskHasChildren}
      isTaskHiddenByCollapsedParent={isTaskHiddenByCollapsedParent}
      getTaskDepth={getTaskDepth}
    />
  );
}

export default App;
