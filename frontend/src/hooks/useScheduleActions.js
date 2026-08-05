import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  applyTemplate,
  createTask,
  deleteTask,
  exportProjectPdf,
  reorderTasks,
  saveTemplate,
  updateScheduleSettings,
  updateTask,
  updateTaskProgress,
} from "../services/api";
import { moveArrayItem } from "../utils/array";
import {
  formatPredecessorForApi,
  formatPredecessorForSchedule,
} from "../utils/taskReferences";
import {
  findIndentParent,
  getTaskDepthFromList,
} from "../utils/taskHierarchy";

/**
 * Owns the scheduler's interaction state (cell editing, selection, view) and
 * every schedule mutation: inline edits, deletion, drag reorder, hierarchy
 * changes, collapse, templates, and PDF export.
 */
function useScheduleActions({
  selectedProjectId,
  selectedProjectIdRef,
  tasks,
  setTasks,
  setScheduleSummary = () => {},
  setScheduleSettings,
  setTemplates,
  loadTasks,
  runOperation,
  showNotice,
  reportRequestError,
  reportValidationError,
}) {
  const [editingCell, setEditingCell] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [progressSelection, setProgressSelection] = useState(null);
  const [planningSelection, setPlanningSelection] = useState(null);
  const [scheduleView, setScheduleView] = useState("table");
  const [templateName, setTemplateName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [pendingActions, setPendingActions] = useState([]);
  const projectGenerationRef = useRef(0);
  const previousProjectIdRef = useRef(selectedProjectId);
  const pendingTokensRef = useRef(new Map());
  const mutationControllersRef = useRef(new Set());

  useEffect(() => {
    const controllers = mutationControllersRef.current;
    const projectChanged = previousProjectIdRef.current !== selectedProjectId;
    previousProjectIdRef.current = selectedProjectId;
    if (!projectChanged) {
      return () => {
        for (const controller of controllers) controller.abort();
      };
    }

    projectGenerationRef.current += 1;
    for (const controller of controllers) {
      controller.abort();
    }
    controllers.clear();
    pendingTokensRef.current.clear();
    const timeoutId = window.setTimeout(() => {
      setPendingActions([]);
      setEditingCell(null);
      setEditValue("");
      setSelectedTaskId(null);
      setProgressSelection(null);
      setPlanningSelection(null);
      setTemplateName("");
      setSelectedTemplateId("");
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      for (const controller of controllers) {
        controller.abort();
      }
    };
  }, [selectedProjectId]);

  const runProjectMutation = useCallback(
    async (key, operation, { onSuccess, onError } = {}) => {
      const projectId = selectedProjectIdRef.current;
      if (!projectId || pendingTokensRef.current.has(key)) return undefined;

      const generation = projectGenerationRef.current;
      const token = Symbol(key);
      const controller = new AbortController();
      pendingTokensRef.current.set(key, token);
      mutationControllersRef.current.add(controller);
      setPendingActions(Array.from(pendingTokensRef.current.keys()));

      const isCurrentProject = () =>
        selectedProjectIdRef.current === projectId &&
        projectGenerationRef.current === generation;

      try {
        const result = await operation(projectId, {
          signal: controller.signal,
        });
        if (isCurrentProject()) await onSuccess?.(result);
        return isCurrentProject() ? result : undefined;
      } catch (error) {
        if (isCurrentProject() && error?.name !== "AbortError") {
          onError?.(error);
        }
        return undefined;
      } finally {
        mutationControllersRef.current.delete(controller);
        if (pendingTokensRef.current.get(key) === token) {
          pendingTokensRef.current.delete(key);
          setPendingActions(Array.from(pendingTokensRef.current.keys()));
        }
      }
    },
    [selectedProjectIdRef]
  );

  const isScheduleMutationActive = useCallback(
    (key) => pendingActions.includes(key),
    [pendingActions]
  );

  const applyTaskResponse = useCallback(
    (data) => {
      setTasks(data.tasks);
      setScheduleSummary(data.summary || null);
    },
    [setScheduleSummary, setTasks]
  );

  const handleCellClick = (task, field) => {
    setEditingCell({ id: task.id ?? "new", field });

    if (field === "predecessor") {
      setEditValue(formatPredecessorForSchedule(task.predecessor, tasks));
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
      const validMilestoneDuration = task.is_milestone && value === 0;
      const validTaskDuration = !task.is_milestone && value >= 1;
      if (
        !Number.isInteger(value) ||
        (!validMilestoneDuration && !validTaskDuration) ||
        value > 36_500
      ) {
        reportValidationError(
          task.is_milestone
            ? "Milestones require zero duration."
            : "Enter a whole number of workdays from 1 to 36500."
        );
        return;
      }
    }

    if (editingCell.field === "predecessor") {
      const predecessor = formatPredecessorForApi(editValue, tasks);

      if (predecessor.error) {
        reportValidationError(predecessor.error);
        return;
      }

      value = predecessor.value;
    }

    if (editingCell.field === "manual_start_date" && !value) {
      value = null;
    }

    if (
      task.id === null &&
      editingCell.field === "name" &&
      !String(value).trim()
    ) {
      reportValidationError("Enter a task name before adding the task.");
      return;
    }

    await runProjectMutation(
      "saveTask",
      (projectId, options) =>
        task.id === null
          ? createTask(projectId, {
              name: editingCell.field === "name" ? value : "New Task",
              duration: editingCell.field === "duration" ? value : 1,
              predecessor:
                editingCell.field === "predecessor" ? value : null,
              manual_start_date:
                editingCell.field === "manual_start_date" ? value : null,
            }, options)
          : updateTask(
              projectId,
              task.id,
              { [editingCell.field]: value },
              options
            ),
      {
        onSuccess: (data) => {
          applyTaskResponse(data);
          setEditingCell(null);
        },
        onError: (error) =>
          reportRequestError("Unable to save task", error),
      }
    );
  };

  const handleCellCancel = () => {
    setEditingCell(null);
    setEditValue("");
  };

  /** Executes a confirmed task deletion (the confirm dialog lives in App). */
  const performTaskDelete = async (id) => {
    await runProjectMutation(
      `deleteTask:${id}`,
      (projectId, options) => deleteTask(projectId, id, options),
      {
        onSuccess: (data) => {
          applyTaskResponse(data);
          showNotice("success", "Task deleted.");
        },
        onError: (error) =>
          reportRequestError("Unable to delete task", error),
      }
    );
  };

  const getEmptyRow = () => ({
    id: null,
    name: "",
    duration: "",
    manual_start_date: "",
    predecessor: "",
  });

  const handleSaveTemplate = async () => {
    if (!selectedProjectId) {
      reportValidationError("Select a project before saving a template.");
      return;
    }

    if (!templateName.trim()) {
      reportValidationError("Enter a template name before saving.");
      return;
    }

    return runOperation("saveTemplate", async () => {
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
    });
  };

  const handleApplyTemplate = async () => {
    if (!selectedProjectId || !selectedTemplateId) {
      reportValidationError("Select a template before applying it.");
      return;
    }

    return runProjectMutation(
      "applyTemplate",
      (projectId, options) =>
        applyTemplate(projectId, selectedTemplateId, options),
      {
        onSuccess: async () => {
          await loadTasks();
          showNotice("success", "Schedule template applied.");
        },
        onError: (error) =>
          reportRequestError("Unable to apply template", error),
      }
    );
  };

  const handleExportProjectPdf = async () => {
    if (!selectedProjectId) {
      reportValidationError("Select a project before exporting.");
      return;
    }

    return runOperation("exportPdf", async () => {
      try {
        await exportProjectPdf(selectedProjectId);
        showNotice("success", "Schedule PDF downloaded.");
      } catch (error) {
        reportRequestError("Unable to export project PDF", error);
      }
    });
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;

    if (!over || active.id === over.id) return;

    const oldIndex = tasks.findIndex((task) => task.id === active.id);
    const newIndex = tasks.findIndex((task) => task.id === over.id);

    const reorderedTasks = moveArrayItem(tasks, oldIndex, newIndex);

    if (pendingTokensRef.current.has("reorderTasks")) return;
    setTasks(reorderedTasks);

    await runProjectMutation(
      "reorderTasks",
      (projectId, options) =>
        reorderTasks(
          projectId,
          reorderedTasks.map((task) => task.id),
          options
        ),
      {
        onError: (error) => {
          setTasks(tasks);
          reportRequestError("Unable to reorder tasks", error);
        },
      }
    );
  };

  const handleToggleCollapse = async (task) => {
    await runProjectMutation(
      `toggleTask:${task.id}`,
      (projectId, options) =>
        updateTask(
          projectId,
          task.id,
          { is_collapsed: task.is_collapsed ? 0 : 1 },
          options
        ),
      {
        onSuccess: applyTaskResponse,
        onError: (error) =>
          reportRequestError("Unable to update task visibility", error),
      }
    );
  };

  // Derived hierarchy lookups: memoized on the task list so grid keystrokes
  // and selection changes don't rebuild them, and stable so consumers can
  // memoize row filtering on top of them.
  const taskMap = useMemo(
    () => new Map(tasks.map((task) => [task.id, task])),
    [tasks]
  );

  const getTaskDepth = useCallback(
    (task) => getTaskDepthFromList(tasks, task),
    [tasks]
  );

  const taskHasChildren = useCallback(
    (taskId) => tasks.some((task) => task.parent_task_id === taskId),
    [tasks]
  );

  const isTaskHiddenByCollapsedParent = useCallback(
    (task) => {
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
    },
    [taskMap]
  );

  const handleIndentTask = async (task) => {
    const parent = findIndentParent(tasks, task.id);
    if (!parent) return;

    await runProjectMutation(
      `indentTask:${task.id}`,
      (projectId, options) =>
        updateTask(
          projectId,
          task.id,
          { parent_task_id: parent.id },
          options
        ),
      {
        onSuccess: applyTaskResponse,
        onError: (error) =>
          reportRequestError("Unable to indent task", error),
      }
    );
  };

  const handleOutdentTask = async (task) => {
    if (!task.parent_task_id) return;

    const parent = taskMap.get(task.parent_task_id);

    await runProjectMutation(
      `outdentTask:${task.id}`,
      (projectId, options) =>
        updateTask(
          projectId,
          task.id,
          { parent_task_id: parent?.parent_task_id || null },
          options
        ),
      {
        onSuccess: applyTaskResponse,
        onError: (error) =>
          reportRequestError("Unable to outdent task", error),
      }
    );
  };

  const handleUpdateScheduleStart = async (scheduleStartDate) => {
    return runProjectMutation(
      "updateScheduleSettings",
      (projectId, options) =>
        updateScheduleSettings(
          projectId,
          { schedule_start_date: scheduleStartDate },
          options
        ),
      {
        onSuccess: async (settings) => {
          setScheduleSettings(settings);
          await loadTasks();
          showNotice("success", "Schedule start date updated.");
        },
        onError: (error) =>
          reportRequestError("Unable to update schedule start date", error),
      }
    );
  };

  const handleUpdateDataDate = async (dataDate) => {
    return runProjectMutation(
      "updateScheduleSettings",
      (projectId, options) =>
        updateScheduleSettings(projectId, { data_date: dataDate }, options),
      {
        onSuccess: async (settings) => {
          setScheduleSettings(settings);
          await loadTasks();
          showNotice("success", "Data Date updated.");
        },
        onError: (error) =>
          reportRequestError("Unable to update Data Date", error),
      }
    );
  };

  const openTaskProgress = useCallback(
    (task) => {
      if (selectedProjectId && task?.id) {
        setProgressSelection({
          projectId: selectedProjectId,
          taskId: task.id,
        });
      }
    },
    [selectedProjectId]
  );

  const closeTaskProgress = useCallback(() => {
    setProgressSelection(null);
  }, []);

  const handleUpdateTaskProgress = async (taskId, progress) => {
    return runProjectMutation(
      `updateProgress:${taskId}`,
      (projectId, options) =>
        updateTaskProgress(projectId, taskId, progress, options),
      {
        onSuccess: (data) => {
          applyTaskResponse(data);
          setProgressSelection(null);
          showNotice("success", "Task progress updated.");
        },
        onError: (error) => {
          if (error?.status === 404) setProgressSelection(null);
          reportRequestError("Unable to update task progress", error);
        },
      }
    );
  };

  const openTaskPlanning = useCallback(
    (task) => {
      if (selectedProjectId && task?.id) {
        setPlanningSelection({
          projectId: selectedProjectId,
          taskId: task.id,
        });
      }
    },
    [selectedProjectId]
  );

  const closeTaskPlanning = useCallback(() => {
    setPlanningSelection(null);
  }, []);

  const handleUpdateTaskPlanning = async (taskId, planning) => {
    return runProjectMutation(
      `updatePlanning:${taskId}`,
      (projectId, options) => updateTask(projectId, taskId, planning, options),
      {
        onSuccess: (data) => {
          applyTaskResponse(data);
          setPlanningSelection(null);
          showNotice("success", "Task planning updated.");
        },
        onError: (error) => {
          if (error?.status === 404) setPlanningSelection(null);
          reportRequestError("Unable to update task planning", error);
        },
      }
    );
  };

  const currentProgressTaskId =
    progressSelection?.projectId === selectedProjectId
      ? progressSelection.taskId
      : null;
  const currentPlanningTaskId =
    planningSelection?.projectId === selectedProjectId
      ? planningSelection.taskId
      : null;

  return {
    editingCell,
    editValue,
    setEditValue,
    selectedTaskId,
    setSelectedTaskId,
    progressTaskId: currentProgressTaskId,
    planningTaskId: currentPlanningTaskId,
    scheduleView,
    setScheduleView,
    templateName,
    setTemplateName,
    selectedTemplateId,
    setSelectedTemplateId,
    handleCellClick,
    handleCellSave,
    handleCellCancel,
    performTaskDelete,
    getEmptyRow,
    handleSaveTemplate,
    handleApplyTemplate,
    handleExportProjectPdf,
    handleDragEnd,
    handleToggleCollapse,
    getTaskDepth,
    taskHasChildren,
    isTaskHiddenByCollapsedParent,
    handleIndentTask,
    handleOutdentTask,
    handleUpdateScheduleStart,
    handleUpdateDataDate,
    openTaskProgress,
    closeTaskProgress,
    handleUpdateTaskProgress,
    openTaskPlanning,
    closeTaskPlanning,
    handleUpdateTaskPlanning,
    isScheduleMutationActive,
  };
}

export default useScheduleActions;
