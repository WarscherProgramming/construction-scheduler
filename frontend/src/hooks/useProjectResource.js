import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchChangeOrders,
  fetchDailyLogs,
  fetchInspections,
  fetchNotesDelays,
  fetchPunchItems,
  fetchProjectCompanies,
  fetchProjects,
  fetchRFIs,
  fetchScheduleSettings,
  fetchSubmittals,
  fetchTasks,
  fetchTemplates,
} from "../services/api";
import { sortByDateDescending } from "../utils/date";
import { parseAppHash } from "../utils/navigation";

/**
 * Owns every server-backed resource (projects, templates, and the
 * project-scoped collections), the concurrency gates, and the loading
 * effects. Project-scoped loaders share one factory: they guard on the
 * selected project, track per-resource loading state, drop stale responses
 * after a project switch, and report failures through the notice system.
 */
function useProjectResource({
  isAuthenticated,
  currentPage,
  selectedProjectId,
  selectedProjectIdRef,
  selectProject,
  navigateTo,
  reportRequestError,
}) {
  const [projects, setProjects] = useState([]);
  const [hasLoadedProjects, setHasLoadedProjects] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [taskProjectId, setTaskProjectId] = useState(null);
  const [scheduleSummary, setScheduleSummary] = useState(null);
  const [scheduleSettings, setScheduleSettings] = useState(null);
  const [taskLoadError, setTaskLoadError] = useState(null);
  const [dailyLogs, setDailyLogs] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [notesDelays, setNotesDelays] = useState([]);
  const [changeOrders, setChangeOrders] = useState([]);
  const [rfis, setRFIs] = useState([]);
  const [submittals, setSubmittals] = useState([]);
  const [punchItems, setPunchItems] = useState([]);
  const [projectCompanies, setProjectCompanies] = useState([]);

  const [activeOperations, setActiveOperations] = useState([]);
  const activeOperationsRef = useRef(new Set());
  const [loadingResources, setLoadingResources] = useState([]);
  const resourceLoadCountsRef = useRef(new Map());

  const runOperation = useCallback(async (key, operation) => {
    if (activeOperationsRef.current.has(key)) return undefined;

    activeOperationsRef.current.add(key);
    setActiveOperations(Array.from(activeOperationsRef.current));

    try {
      return await operation();
    } finally {
      activeOperationsRef.current.delete(key);
      setActiveOperations(Array.from(activeOperationsRef.current));
    }
  }, []);

  const isOperationActive = useCallback(
    (key) => activeOperations.includes(key),
    [activeOperations]
  );

  const runResourceLoad = useCallback(async (key, operation) => {
    const currentCount = resourceLoadCountsRef.current.get(key) || 0;
    resourceLoadCountsRef.current.set(key, currentCount + 1);
    setLoadingResources(Array.from(resourceLoadCountsRef.current.keys()));

    try {
      return await operation();
    } finally {
      const remainingCount =
        (resourceLoadCountsRef.current.get(key) || 1) - 1;

      if (remainingCount > 0) {
        resourceLoadCountsRef.current.set(key, remainingCount);
      } else {
        resourceLoadCountsRef.current.delete(key);
      }

      setLoadingResources(Array.from(resourceLoadCountsRef.current.keys()));
    }
  }, []);

  const isResourceLoading = useCallback(
    (key) => loadingResources.includes(key),
    [loadingResources]
  );

  // Shared loader for project-scoped resources.
  const loadProjectResource = useCallback(
    async (key, fetcher, applyData, errorContext, onError) => {
      const projectId = selectedProjectId;
      if (!projectId) return undefined;

      return runResourceLoad(key, async () => {
        try {
          const data = await fetcher(projectId);

          if (selectedProjectIdRef.current === projectId) {
            applyData(data);
          }
        } catch (error) {
          if (selectedProjectIdRef.current === projectId) {
            onError?.(error);
            reportRequestError(errorContext, error);
          }
        }
      });
    },
    [
      reportRequestError,
      runResourceLoad,
      selectedProjectId,
      selectedProjectIdRef,
    ]
  );

  // Projects reconcile the requested route against what actually exists.
  const loadProjects = useCallback(async () => {
    return runResourceLoad("projects", async () => {
      try {
        const data = await fetchProjects();
        setProjects(data.projects);
        const route = parseAppHash(window.location.hash);
        const requestedProjectId = route.projectId;
        const requestedProjectExists = data.projects.some(
          (project) => project.id === requestedProjectId
        );
        const nextProjectId =
          route.page === "home"
            ? null
            : requestedProjectExists
              ? requestedProjectId
              : data.projects[0]?.id ?? null;

        selectProject(nextProjectId);

        if (route.page !== "home" && !requestedProjectExists) {
          navigateTo(
            nextProjectId ? "projectDashboard" : "home",
            nextProjectId,
            { replace: true }
          );
        }
      } catch (error) {
        reportRequestError("Unable to load projects", error);
      } finally {
        setHasLoadedProjects(true);
      }
    });
  }, [navigateTo, reportRequestError, runResourceLoad, selectProject]);

  const loadTemplates = useCallback(async () => {
    return runResourceLoad("templates", async () => {
      try {
        const data = await fetchTemplates();
        setTemplates(data.templates);
      } catch (error) {
        reportRequestError("Unable to load templates", error);
      }
    });
  }, [reportRequestError, runResourceLoad]);

  const loadTasks = useCallback(() => {
    setTaskLoadError(null);
    return loadProjectResource(
      "tasks",
      fetchTasks,
      (data) => {
        setTasks(data.tasks);
        setTaskProjectId(selectedProjectIdRef.current);
        setScheduleSummary(data.summary || null);
        setTaskLoadError(null);
      },
      "Unable to load tasks",
      () => {
        setTaskProjectId(selectedProjectIdRef.current);
        setScheduleSummary(null);
        setTaskLoadError("Unable to load the project schedule.");
      }
    );
  }, [loadProjectResource, selectedProjectIdRef]);

  const loadScheduleSettings = useCallback(
    () =>
      loadProjectResource(
        "scheduleSettings",
        fetchScheduleSettings,
        setScheduleSettings,
        "Unable to load schedule settings"
      ),
    [loadProjectResource]
  );

  const loadDailyLogs = useCallback(
    () =>
      loadProjectResource(
        "dailyLogs",
        fetchDailyLogs,
        (data) => setDailyLogs(sortByDateDescending(data.daily_logs || [])),
        "Unable to load daily logs"
      ),
    [loadProjectResource]
  );

  const loadInspections = useCallback(
    () =>
      loadProjectResource(
        "inspections",
        fetchInspections,
        (data) => setInspections(sortByDateDescending(data.inspections || [])),
        "Unable to load inspections"
      ),
    [loadProjectResource]
  );

  const loadNotesDelays = useCallback(
    () =>
      loadProjectResource(
        "notesDelays",
        fetchNotesDelays,
        (data) =>
          setNotesDelays(sortByDateDescending(data.notes_delays || [])),
        "Unable to load notes and delays"
      ),
    [loadProjectResource]
  );

  const loadChangeOrders = useCallback(
    () =>
      loadProjectResource(
        "changeOrders",
        fetchChangeOrders,
        (data) =>
          setChangeOrders(sortByDateDescending(data.change_orders || [])),
        "Unable to load change orders"
      ),
    [loadProjectResource]
  );

  const loadRFIs = useCallback(
    () =>
      loadProjectResource(
        "rfis",
        fetchRFIs,
        (data) => setRFIs(data.rfis || []),
        "Unable to load RFIs"
      ),
    [loadProjectResource]
  );

  const loadSubmittals = useCallback(
    () =>
      loadProjectResource(
        "submittals",
        fetchSubmittals,
        (data) => setSubmittals(data.submittals || []),
        "Unable to load Submittals"
      ),
    [loadProjectResource]
  );

  const loadPunchItems = useCallback(
    () =>
      loadProjectResource(
        "punchItems",
        fetchPunchItems,
        (data) => setPunchItems(data.punch_items || []),
        "Unable to load Punch Items"
      ),
    [loadProjectResource]
  );

  const loadProjectCompanies = useCallback(
    () =>
      loadProjectResource(
        "companies",
        fetchProjectCompanies,
        (data) => setProjectCompanies(data.companies || []),
        "Unable to load project companies"
      ),
    [loadProjectResource]
  );

  const clearAllData = useCallback(() => {
    setProjects([]);
    setHasLoadedProjects(false);
    setTasks([]);
    setTaskProjectId(null);
    setScheduleSummary(null);
    setScheduleSettings(null);
    setTaskLoadError(null);
    setTemplates([]);
    setDailyLogs([]);
    setInspections([]);
    setNotesDelays([]);
    setChangeOrders([]);
    setRFIs([]);
    setSubmittals([]);
    setPunchItems([]);
    setProjectCompanies([]);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return undefined;

    const timeoutId = window.setTimeout(() => {
      void Promise.all([loadProjects(), loadTemplates()]);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [isAuthenticated, loadProjects, loadTemplates]);

  useEffect(() => {
    if (!isAuthenticated || !hasLoadedProjects || !selectedProjectId) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setTasks([]);
      setTaskProjectId(null);
      setScheduleSummary(null);
      setScheduleSettings(null);
      setTaskLoadError(null);
      setDailyLogs([]);
      setInspections([]);
      setNotesDelays([]);
      setChangeOrders([]);
      setRFIs([]);
      setSubmittals([]);
      setPunchItems([]);
      setProjectCompanies([]);

    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [
    isAuthenticated,
    hasLoadedProjects,
    selectedProjectId,
  ]);

  useEffect(() => {
    if (!isAuthenticated || !hasLoadedProjects || !selectedProjectId) {
      return undefined;
    }

    const pageLoaders = {
      scheduler: [loadTasks, loadScheduleSettings],
      dailyLogs: [loadDailyLogs, loadProjectCompanies],
      inspections: [loadInspections, loadProjectCompanies],
      notesDelays: [loadNotesDelays, loadProjectCompanies],
      changeOrders: [loadChangeOrders, loadProjectCompanies],
      rfis: [loadRFIs, loadProjectCompanies],
      submittals: [loadSubmittals, loadProjectCompanies],
      punchItems: [loadPunchItems, loadProjectCompanies],
      projectSettings: [loadProjectCompanies],
    };

    const loaders = pageLoaders[currentPage] || [];
    const timeoutId = window.setTimeout(() => {
      void Promise.all(loaders.map((load) => load()));
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [
    currentPage,
    hasLoadedProjects,
    isAuthenticated,
    loadChangeOrders,
    loadDailyLogs,
    loadInspections,
    loadNotesDelays,
    loadProjectCompanies,
    loadPunchItems,
    loadRFIs,
    loadScheduleSettings,
    loadSubmittals,
    loadTasks,
    selectedProjectId,
  ]);

  return {
    projects,
    setProjects,
    hasLoadedProjects,
    templates,
    setTemplates,
    tasks,
    setTasks,
    taskProjectId,
    scheduleSummary,
    setScheduleSummary,
    scheduleSettings,
    setScheduleSettings,
    taskLoadError,
    dailyLogs,
    inspections,
    notesDelays,
    changeOrders,
    rfis,
    submittals,
    punchItems,
    projectCompanies,
    loadProjects,
    loadTemplates,
    loadTasks,
    loadScheduleSettings,
    loadDailyLogs,
    loadInspections,
    loadNotesDelays,
    loadChangeOrders,
    loadRFIs,
    loadSubmittals,
    loadPunchItems,
    loadProjectCompanies,
    clearAllData,
    runOperation,
    isOperationActive,
    isResourceLoading,
  };
}

export default useProjectResource;
