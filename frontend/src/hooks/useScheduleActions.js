import { useCallback, useMemo, useState } from "react";

import {
  applyTemplate,
  createTask,
  deleteTask,
  exportProjectPdf,
  reorderTasks,
  saveTemplate,
  updateTask,
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


function taskMutationPayload(task) {
  return {
    name: task.name,
    duration: task.duration,
    predecessor: task.predecessor,
    dependency_type: task.dependency_type,
    lag_days: task.lag_days,
    manual_start_date: task.manual_start_date,
    parent_task_id: task.parent_task_id,
    is_collapsed: task.is_collapsed,
  };
}

/**
 * Owns the scheduler's interaction state (cell editing, selection, view) and
 * every schedule mutation: inline edits, deletion, drag reorder, hierarchy
 * changes, collapse, templates, and PDF export.
 */
function useScheduleActions({
  selectedProjectId,
  tasks,
  setTasks,
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
  const [scheduleView, setScheduleView] = useState("table");
  const [templateName, setTemplateName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

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
    }

    if (editingCell.field === "predecessor") {
      const predecessor = formatPredecessorForApi(editValue, tasks);

      if (predecessor.error) {
        reportValidationError(predecessor.error);
        return;
      }

      value = predecessor.value;
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
              ...taskMutationPayload(task),
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

  /** Executes a confirmed task deletion (the confirm dialog lives in App). */
  const performTaskDelete = async (id) => {
    try {
      const data = await deleteTask(selectedProjectId, id);
      setTasks(data.tasks);
      showNotice("success", "Task deleted.");
    } catch (error) {
      reportRequestError("Unable to delete task", error);
    }
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

    return runOperation("applyTemplate", async () => {
      try {
        await applyTemplate(selectedProjectId, selectedTemplateId);
        await loadTasks();
        showNotice("success", "Schedule template applied.");
      } catch (error) {
        reportRequestError("Unable to apply template", error);
      }
    });
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
      ...taskMutationPayload(task),
      is_collapsed: task.is_collapsed ? 0 : 1,
    };

    try {
      const data = await updateTask(selectedProjectId, task.id, updatedTask);
      setTasks(data.tasks);
    } catch (error) {
      reportRequestError("Unable to update task visibility", error);
    }
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

  return {
    editingCell,
    editValue,
    setEditValue,
    selectedTaskId,
    setSelectedTaskId,
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
  };
}

export default useScheduleActions;
