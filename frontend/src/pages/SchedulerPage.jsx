import { useEffect, useRef, useState } from "react";
import { closestCenter, DndContext } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import GanttChart from "../components/GanttChart";
import FormField from "../components/FormField";
import LoadingState from "../components/LoadingState";
import NewTaskInput from "../components/NewTaskInput";
import SortableTaskRow from "../components/SortableTaskRow";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import {
  formatPredecessorForApi,
  formatPredecessorForSchedule,
  getScheduleTaskNumber,
} from "../utils/taskReferences";
import { findIndentParent } from "../utils/taskHierarchy";

/** Grid columns reachable by the roving keyboard cursor, in visual order. */
const EDITABLE_FIELDS = ["name", "duration", "manual_start_date", "predecessor"];

function SchedulerPage({
  projectName,
  tasks,
  templates,
  selectedProjectId,
  selectedTaskId,
  editingCell,
  editValue,
  templateName,
  selectedTemplateId,
  scheduleView,
  setSelectedTaskId,
  setEditValue,
  setTemplateName,
  setSelectedTemplateId,
  setScheduleView,
  onNavigate,
  onSaveTemplate,
  onApplyTemplate,
  onExport,
  isSavingTemplate = false,
  isApplyingTemplate = false,
  isExporting = false,
  isLoadingTasks = false,
  isLoadingTemplates = false,
  onLogout,
  onDragEnd,
  onCellClick,
  onCellSave,
  onCellCancel,
  onDelete,
  onIndent,
  onOutdent,
  onToggleCollapse,
  getEmptyRow,
  formatDate,
  taskHasChildren,
  isTaskHiddenByCollapsedParent,
  getTaskDepth,
}) {
  const visibleTasks = tasks.filter(
    (task) => !isTaskHiddenByCollapsedParent(task)
  );
  const selectedTask = tasks.find((task) => task.id === selectedTaskId);
  const selectedDisplayId = selectedTask
    ? getScheduleTaskNumber(tasks, selectedTask.id)
    : null;
  const canIndentSelectedTask = Boolean(
    selectedTask && findIndentParent(tasks, selectedTask.id)
  );
  const canOutdentSelectedTask = Boolean(selectedTask?.parent_task_id);

  // Roving cell cursor (Excel-style): one tab stop for the grid, arrows and
  // Tab move between editable cells, Enter activates the focused cell.
  const [focusedCell, setFocusedCell] = useState({ row: 0, field: "name" });
  const tableRegionRef = useRef(null);
  const previousEditingCellRef = useRef(editingCell);

  const effectiveFocus = visibleTasks.length
    ? {
        row: Math.min(focusedCell.row, visibleTasks.length - 1),
        field: focusedCell.field,
      }
    : null;

  const moveFocusTo = (row, field) => {
    setFocusedCell({ row, field });
    tableRegionRef.current
      ?.querySelector(`[data-cell="${row}:${field}"]`)
      ?.focus();
  };

  const handleCellNavigate = (event, row, field) => {
    const colIndex = EDITABLE_FIELDS.indexOf(field);
    const lastRow = visibleTasks.length - 1;
    const lastCol = EDITABLE_FIELDS.length - 1;
    let targetRow = row;
    let targetCol = colIndex;

    switch (event.key) {
      case "ArrowRight":
        targetCol = Math.min(colIndex + 1, lastCol);
        break;
      case "ArrowLeft":
        targetCol = Math.max(colIndex - 1, 0);
        break;
      case "ArrowDown":
        targetRow = Math.min(row + 1, lastRow);
        break;
      case "ArrowUp":
        targetRow = Math.max(row - 1, 0);
        break;
      case "Tab": {
        const step = event.shiftKey ? -1 : 1;
        const flatIndex = row * EDITABLE_FIELDS.length + colIndex + step;

        // At the grid's boundaries, let Tab continue out of the grid.
        if (
          flatIndex < 0 ||
          flatIndex > lastRow * EDITABLE_FIELDS.length + lastCol
        ) {
          return;
        }

        targetRow = Math.floor(flatIndex / EDITABLE_FIELDS.length);
        targetCol = flatIndex % EDITABLE_FIELDS.length;
        break;
      }
      default:
        return;
    }

    event.preventDefault();
    moveFocusTo(targetRow, EDITABLE_FIELDS[targetCol]);
  };

  // Clicking a cell moves the cursor there so keyboard flow continues from it.
  const handleGridCellClick = (task, field) => {
    if (EDITABLE_FIELDS.includes(field)) {
      const row = visibleTasks.findIndex(
        (candidate) => candidate.id === task.id
      );

      if (row >= 0) setFocusedCell({ row, field });
    }

    onCellClick(task, field);
  };

  // When an editor closes (save or cancel), return focus to its grid cell.
  useEffect(() => {
    const wasEditing = previousEditingCellRef.current;
    previousEditingCellRef.current = editingCell;

    if (!wasEditing || editingCell || wasEditing.id === "new") {
      return undefined;
    }

    const frame = requestAnimationFrame(() => {
      tableRegionRef.current
        ?.querySelector(
          `[data-cell="${focusedCell.row}:${focusedCell.field}"]`
        )
        ?.focus();
    });

    return () => cancelAnimationFrame(frame);
  }, [editingCell, focusedCell]);

  // Inline cell validation: messages surface next to the cell being edited.
  const validateCell = (field, value) => {
    if (field === "duration") {
      const days = Number(value);

      if (!Number.isInteger(days) || days < 1) {
        return "Enter a whole number of workdays (1 or more).";
      }

      return null;
    }

    if (field === "predecessor") {
      return formatPredecessorForApi(value, tasks).error;
    }

    return null;
  };

  const schedulerControls = (
    <>
      <div className="schedule-view-controls">
        <h2 className="sidebar-heading">View</h2>
        <Button
          onClick={() => setScheduleView("table")}
          aria-pressed={scheduleView === "table"}
        >
          Table
        </Button>
        <Button
          onClick={() => setScheduleView("gantt")}
          aria-pressed={scheduleView === "gantt"}
        >
          Gantt
        </Button>
      </div>

      <Card title="Templates" style={{ marginBottom: "var(--space-4)" }}>
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            onSaveTemplate();
          }}
          style={{ gap: "8px", marginBottom: "16px" }}
        >
          <FormField label="Template name" htmlFor="template-name" required>
            <input
              id="template-name"
              className="field-control"
              required
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
            />
          </FormField>
          <Button
            type="submit"
            variant="primary"
            disabled={isSavingTemplate}
            aria-busy={isSavingTemplate}
          >
            {isSavingTemplate ? "Saving template…" : "Save Template"}
          </Button>
        </form>

        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            onApplyTemplate();
          }}
          style={{ gap: "8px" }}
        >
          <FormField label="Saved template" htmlFor="saved-template" required>
            <select
              id="saved-template"
              className="field-control"
              required
              disabled={isLoadingTemplates}
              value={selectedTemplateId}
              onChange={(event) => setSelectedTemplateId(event.target.value)}
            >
              <option value="">
                {isLoadingTemplates ? "Loading templates…" : "Select template"}
              </option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                </option>
              ))}
            </select>
          </FormField>
          <Button
            type="submit"
            variant="primary"
            disabled={isApplyingTemplate}
            aria-busy={isApplyingTemplate}
          >
            {isApplyingTemplate ? "Applying template…" : "Apply Template"}
          </Button>
        </form>
      </Card>

      <Button
        block
        onClick={onExport}
        disabled={!selectedProjectId || isExporting}
        aria-busy={isExporting}
      >
        {isExporting ? "Exporting PDF…" : "Export Schedule as PDF"}
      </Button>
    </>
  );

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="scheduler"
      onNavigate={onNavigate}
      onLogout={onLogout}
      sidebarExtras={schedulerControls}
      mainClassName="scheduler-main"
    >
        <PageHeader title="Schedule" />

        <div className="schedule-toolbar">
          <div className="schedule-toolbar-selection">
            <p>
              {selectedTask
                ? `Task ${selectedDisplayId} selected`
                : "Select a task to change its hierarchy"}
            </p>
            <div
              className="schedule-hierarchy-actions"
              aria-label="Selected task hierarchy"
            >
              <button
                type="button"
                onClick={() => onIndent(selectedTask)}
                disabled={!canIndentSelectedTask}
                title="Move selected task one level deeper"
              >
                Indent
              </button>
              <button
                type="button"
                onClick={() => onOutdent(selectedTask)}
                disabled={!canOutdentSelectedTask}
                title="Move selected task one level up"
              >
                Outdent
              </button>
            </div>
            <span className="schedule-task-count">
              {tasks.length} {tasks.length === 1 ? "task" : "tasks"}
              {visibleTasks.length !== tasks.length &&
                ` · ${visibleTasks.length} visible`}
            </span>
          </div>
          <details className="dependency-help">
            <summary>Dependency format help</summary>
            <div>
              <p>
                Enter the predecessor&rsquo;s ID from the first column for
                Finish-to-Start. Add <code>SS</code> for Start-to-Start and{" "}
                <code>+days</code> for lag.
              </p>
              <p>
                Examples: <code>2</code>, <code>2+3</code>,{" "}
                <code>1.2SS</code>, <code>1.2SS+4</code>.
              </p>
            </div>
          </details>
        </div>

        {isLoadingTasks ? (
          <LoadingState message="Loading project schedule…" />
        ) : scheduleView === "table" ? (
          <DndContext collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <div
              ref={tableRegionRef}
              className="table-scroll-region schedule-table-region"
              role="region"
              aria-label="Project schedule"
              tabIndex={0}
            >
            {tasks.length === 0 && (
              <div className="schedule-empty-state" role="status">
                No tasks yet. Use Add task below to create the first schedule
                item.
              </div>
            )}
            <table className="schedule-table">
              <caption className="visually-hidden">
                Editable project schedule
              </caption>
              <thead>
                <tr>
                  {[
                    { label: "ID", width: "80px", align: "center" },
                    { label: "Task", width: "470px", align: "left" },
                    { label: "Duration", width: "90px", align: "center" },
                    { label: "Start", width: "120px", align: "center" },
                    { label: "End", width: "120px", align: "center" },
                    {
                      label: "Predecessor",
                      width: "130px",
                      align: "center",
                    },
                    { label: "Actions", width: "90px", align: "center" },
                  ].map((column, columnIndex) => (
                    <th
                      key={column.label}
                      scope="col"
                      className={
                        columnIndex < 2
                          ? `schedule-sticky-column schedule-sticky-${columnIndex}`
                          : undefined
                      }
                      style={{
                        width: column.width,
                        textAlign: column.align,
                      }}
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>

              <SortableContext
                items={visibleTasks.map((task) => task.id)}
                strategy={verticalListSortingStrategy}
              >
                <tbody>
                  {visibleTasks.map((task, index) => (
                      <SortableTaskRow
                        key={task.id}
                        task={task}
                        index={index}
                        displayId={getScheduleTaskNumber(tasks, task.id)}
                        displayPredecessor={formatPredecessorForSchedule(
                          task.predecessor,
                          tasks
                        )}
                        selectedTaskId={selectedTaskId}
                        setSelectedTaskId={setSelectedTaskId}
                        editingCell={editingCell}
                        editValue={editValue}
                        setEditValue={setEditValue}
                        handleCellClick={handleGridCellClick}
                        handleCellSave={onCellSave}
                        handleCellCancel={onCellCancel}
                        handleDelete={onDelete}
                        handleToggleCollapse={onToggleCollapse}
                        formatDate={formatDate}
                        hasChildren={taskHasChildren(task.id)}
                        depth={getTaskDepth(task)}
                        validateCell={validateCell}
                        focusedField={
                          effectiveFocus && effectiveFocus.row === index
                            ? effectiveFocus.field
                            : null
                        }
                        onCellNavigate={handleCellNavigate}
                      />
                    ))}

                  <tr className="schedule-new-row">
                    <td className="schedule-sticky-column schedule-sticky-0"></td>
                    <td className="schedule-sticky-column schedule-sticky-1">
                      {editingCell?.id === "new" &&
                      editingCell.field === "name" ? (
                        <NewTaskInput
                          value={editValue}
                          onChange={setEditValue}
                          onSave={() => onCellSave(getEmptyRow())}
                          onCancel={onCellCancel}
                        />
                      ) : (
                        <button
                          type="button"
                          className="schedule-cell-button"
                          onClick={() => onCellClick(getEmptyRow(), "name")}
                        >
                          + Add task
                        </button>
                      )}
                    </td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td></td>
                  </tr>
                </tbody>
              </SortableContext>
            </table>
            </div>
          </DndContext>
        ) : (
          <div
            className="gantt-scroll-region"
            role="region"
            aria-label="Project Gantt chart"
            tabIndex={0}
          >
            <GanttChart tasks={tasks} selectedTaskId={selectedTaskId} />
          </div>
        )}
    </ProjectLayout>
  );
}

export default SchedulerPage;
