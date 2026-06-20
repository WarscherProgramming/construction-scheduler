import { closestCenter, DndContext } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import GanttChart from "../components/GanttChart";
import FormField from "../components/FormField";
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
          onClick={() => onNavigate("projectDashboard")}
          style={buttonStyle}
        >
          Project Dashboard
        </button>

        <div style={{ marginTop: "15px", marginBottom: "15px" }}>
          <h3>View</h3>
          <button onClick={() => setScheduleView("table")} style={buttonStyle}>
            Table
          </button>
          <button onClick={() => setScheduleView("gantt")} style={buttonStyle}>
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
          <h3 style={{ marginTop: 0 }}>Templates</h3>
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
            <button type="submit" style={buttonStyle}>
              Save Template
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
                value={selectedTemplateId}
                onChange={(event) => setSelectedTemplateId(event.target.value)}
              >
                <option value="">Select template</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </FormField>
            <button type="submit" style={buttonStyle}>
              Apply Template
            </button>
          </form>
        </div>

        <button
          onClick={onExport}
          disabled={!selectedProjectId}
          style={buttonStyle}
        >
          Export Schedule as PDF
        </button>

        <div style={{ marginTop: "auto" }}>
          <button onClick={onLogout} style={buttonStyle}>
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

        {scheduleView === "table" && (
          <DndContext collisionDetection={closestCenter} onDragEnd={onDragEnd}>
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
                  {[
                    { label: "Id", width: "50px", align: "center" },
                    { label: "Task", width: "500px", align: "left" },
                    { label: "Duration", width: "90px", align: "center" },
                    { label: "Start", width: "120px", align: "center" },
                    { label: "End", width: "120px", align: "center" },
                    {
                      label: "Predecessor",
                      width: "130px",
                      align: "center",
                    },
                    { label: "Actions", width: "190px", align: "center" },
                  ].map((column) => (
                    <th
                      key={column.label}
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

                  <tr>
                    <td style={{ border: "1px solid #ddd" }}></td>
                    <td style={{ padding: "8px", border: "1px solid #ddd" }}>
                      {editingCell?.id === "new" &&
                      editingCell.field === "name" ? (
                        <input
                          autoFocus
                          aria-label="New task name"
                          className="schedule-cell-input"
                          value={editValue}
                          onChange={(event) => setEditValue(event.target.value)}
                          onBlur={() => onCellSave(getEmptyRow())}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              onCellSave(getEmptyRow());
                            }

                            if (event.key === "Escape") {
                              event.preventDefault();
                              onCellCancel();
                            }
                          }}
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
          </DndContext>
        )}

        {scheduleView === "gantt" && (
          <div style={{ marginTop: "20px" }}>
            <GanttChart tasks={tasks} selectedTaskId={selectedTaskId} />
          </div>
        )}
      </main>
    </div>
  );
}

export default SchedulerPage;
