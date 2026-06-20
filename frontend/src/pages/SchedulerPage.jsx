import { closestCenter, DndContext } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import GanttChart from "../components/GanttChart";
import FormField from "../components/FormField";
import LoadingState from "../components/LoadingState";
import NewTaskInput from "../components/NewTaskInput";
import SkipLink from "../components/SkipLink";
import SortableTaskRow from "../components/SortableTaskRow";
import { buttonStyle } from "../styles";

function SchedulerPage({
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

  return (
    <div className="app-shell scheduler-shell">
      <SkipLink />
      <aside className="app-sidebar scheduler-sidebar">
        <button
          onClick={() => onNavigate("projectDashboard")}
          style={buttonStyle}
        >
          Project Dashboard
        </button>

        <div className="schedule-view-controls">
          <h2 className="sidebar-heading">View</h2>
          <button
            onClick={() => setScheduleView("table")}
            aria-pressed={scheduleView === "table"}
            style={buttonStyle}
          >
            Table
          </button>
          <button
            onClick={() => setScheduleView("gantt")}
            aria-pressed={scheduleView === "gantt"}
            style={buttonStyle}
          >
            Gantt
          </button>
        </div>

        <div
          style={{
            padding: "15px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            marginBottom: "15px",
          }}
        >
          <h2 className="sidebar-heading" style={{ marginTop: 0 }}>
            Templates
          </h2>
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
            <button
              type="submit"
              className="button-primary"
              disabled={isSavingTemplate}
              aria-busy={isSavingTemplate}
              style={buttonStyle}
            >
              {isSavingTemplate ? "Saving template…" : "Save Template"}
            </button>
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
            <button
              type="submit"
              className="button-primary"
              disabled={isApplyingTemplate}
              aria-busy={isApplyingTemplate}
              style={buttonStyle}
            >
              {isApplyingTemplate ? "Applying template…" : "Apply Template"}
            </button>
          </form>
        </div>

        <button
          onClick={onExport}
          disabled={!selectedProjectId || isExporting}
          aria-busy={isExporting}
          style={buttonStyle}
        >
          {isExporting ? "Exporting PDF…" : "Export Schedule as PDF"}
        </button>

        <div className="sidebar-footer">
          <button onClick={onLogout} style={buttonStyle}>
            Logout
          </button>
        </div>
      </aside>

      <main
        id="main-content"
        className="app-main scheduler-main"
        tabIndex={-1}
      >
        <h1
          style={{
            textAlign: "center",
            width: "100%",
            marginBottom: "20px",
          }}
        >
          Schedule
        </h1>

        <div className="schedule-toolbar">
          <p>
            {tasks.length} {tasks.length === 1 ? "task" : "tasks"}
            {visibleTasks.length !== tasks.length &&
              ` · ${visibleTasks.length} visible`}
          </p>
          <details className="dependency-help">
            <summary>Dependency format help</summary>
            <div>
              <p>
                Enter a task ID for Finish-to-Start. Add <code>SS</code> for
                Start-to-Start and <code>+days</code> for lag.
              </p>
              <p>
                Examples: <code>12</code>, <code>12+3</code>,{" "}
                <code>12SS</code>, <code>12SS+4</code>.
              </p>
            </div>
          </details>
        </div>

        {isLoadingTasks ? (
          <LoadingState message="Loading project schedule…" />
        ) : scheduleView === "table" ? (
          <DndContext collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <div
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
            <table
              className="schedule-table"
              style={{
                width: "100%",
                minWidth: "1400px",
                borderCollapse: "separate",
                borderSpacing: 0,
                marginTop: "20px",
                tableLayout: "fixed",
              }}
            >
              <caption className="visually-hidden">
                Editable project schedule
              </caption>
              <thead>
                <tr>
                  {[
                    { label: "Id", width: "80px", align: "center" },
                    { label: "Task", width: "470px", align: "left" },
                    { label: "Duration", width: "90px", align: "center" },
                    { label: "Start", width: "120px", align: "center" },
                    { label: "End", width: "120px", align: "center" },
                    {
                      label: "Predecessor",
                      width: "130px",
                      align: "center",
                    },
                    { label: "Actions", width: "190px", align: "center" },
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
                        padding: "10px",
                        background: "#f3f4f6",
                        border: "1px solid #ddd",
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
                        selectedTaskId={selectedTaskId}
                        setSelectedTaskId={setSelectedTaskId}
                        editingCell={editingCell}
                        editValue={editValue}
                        setEditValue={setEditValue}
                        handleCellClick={onCellClick}
                        handleCellSave={onCellSave}
                        handleCellCancel={onCellCancel}
                        handleDelete={onDelete}
                        handleIndent={onIndent}
                        handleOutdent={onOutdent}
                        handleToggleCollapse={onToggleCollapse}
                        formatDate={formatDate}
                        hasChildren={taskHasChildren(task.id)}
                        depth={getTaskDepth(task)}
                        canIndent={
                          tasks.findIndex(
                            (candidate) => candidate.id === task.id
                          ) > 0
                        }
                        canOutdent={Boolean(task.parent_task_id)}
                      />
                    ))}

                  <tr className="schedule-new-row">
                    <td
                      className="schedule-sticky-column schedule-sticky-0"
                      style={{ border: "1px solid #ddd" }}
                    ></td>
                    <td
                      className="schedule-sticky-column schedule-sticky-1"
                      style={{ padding: "8px", border: "1px solid #ddd" }}
                    >
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
                    <td style={{ border: "1px solid #ddd" }}></td>
                    <td style={{ border: "1px solid #ddd" }}></td>
                    <td style={{ border: "1px solid #ddd" }}></td>
                    <td style={{ border: "1px solid #ddd" }}></td>
                    <td style={{ border: "1px solid #ddd" }}></td>
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
      </main>
    </div>
  );
}

export default SchedulerPage;
