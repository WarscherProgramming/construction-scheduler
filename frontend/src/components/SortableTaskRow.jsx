import { useRef } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";


function CellEditor({
  label,
  type = "text",
  placeholder,
  value,
  onChange,
  onSave,
  onCancel,
}) {
  const skipBlurSave = useRef(false);

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      skipBlurSave.current = true;
      Promise.resolve(onSave()).finally(() => {
        skipBlurSave.current = false;
      });
    }

    if (event.key === "Escape") {
      event.preventDefault();
      skipBlurSave.current = true;
      onCancel();
    }
  };

  return (
    <input
      autoFocus
      aria-label={label}
      className="schedule-cell-input"
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={() => {
        if (!skipBlurSave.current) onSave();
      }}
    />
  );
}

function EditButton({ label, children, onEdit, style }) {
  return (
    <button
      type="button"
      className="schedule-cell-button"
      aria-label={`Edit ${label}`}
      onClick={(event) => {
        event.stopPropagation();
        onEdit();
      }}
      style={style}
    >
      {children}
    </button>
  );
}

function SortableTaskRow({
  task,
  index,
  selectedTaskId,
  setSelectedTaskId,
  editingCell,
  editValue,
  setEditValue,
  handleCellClick,
  handleCellSave,
  handleCellCancel,
  handleDelete,
  handleIndent,
  handleOutdent,
  handleToggleCollapse,
  formatDate,
  hasChildren,
  depth,
  canIndent,
  canOutdent,
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id });

  const rowStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    background:
      selectedTaskId === task.id
        ? "#e0f2fe"
        : index % 2 === 0
          ? "#ffffff"
          : "#f9fafb",
  };

  const isEditing = (field) =>
    editingCell?.id === task.id && editingCell.field === field;

  return (
    <tr
      ref={setNodeRef}
      style={rowStyle}
      onClick={() => setSelectedTaskId(task.id)}
    >
      <td style={{ padding: "4px", border: "1px solid #ddd" }}>
        <button
          type="button"
          className="schedule-icon-button"
          aria-label={`Reorder task ${task.id}: ${task.name}`}
          title="Drag to reorder. Use Space and arrow keys with a keyboard."
          onClick={(event) => event.stopPropagation()}
          {...attributes}
          {...listeners}
        >
          <span aria-hidden="true">Move</span>
          <span style={{ marginLeft: "4px" }}>{task.id}</span>
        </button>
      </td>

      <td style={{ padding: "4px", border: "1px solid #ddd" }}>
        {isEditing("name") ? (
          <CellEditor
            label={`Task ${task.id} name`}
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              paddingLeft: `${depth * 20}px`,
            }}
          >
            <EditButton
              label={`task ${task.id} name`}
              onEdit={() => handleCellClick(task, "name")}
              style={{
                flex: 1,
                fontWeight: hasChildren ? "600" : "400",
              }}
            >
              {task.name}
            </EditButton>

            {hasChildren && (
              <button
                type="button"
                className="schedule-icon-button"
                aria-label={`${task.is_collapsed ? "Expand" : "Collapse"} ${
                  task.name
                }`}
                aria-expanded={!task.is_collapsed}
                onClick={(event) => {
                  event.stopPropagation();
                  handleToggleCollapse(task);
                }}
              >
                <span aria-hidden="true">
                  {task.is_collapsed ? "Expand" : "Collapse"}
                </span>
              </button>
            )}
          </div>
        )}
      </td>

      <td style={{ padding: "4px", border: "1px solid #ddd" }}>
        {isEditing("duration") ? (
          <CellEditor
            label={`Task ${task.id} duration`}
            type="number"
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${task.id} duration`}
            onEdit={() => handleCellClick(task, "duration")}
          >
            {task.duration}
          </EditButton>
        )}
      </td>

      <td style={{ padding: "4px", border: "1px solid #ddd" }}>
        {isEditing("manual_start_date") ? (
          <CellEditor
            label={`Task ${task.id} start date`}
            type="date"
            value={editValue || ""}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${task.id} start date`}
            onEdit={() => handleCellClick(task, "manual_start_date")}
          >
            {formatDate(task.start_date)}
          </EditButton>
        )}
      </td>

      <td style={{ padding: "8px", border: "1px solid #ddd" }}>
        {formatDate(task.end_date)}
      </td>

      <td style={{ padding: "4px", border: "1px solid #ddd" }}>
        {isEditing("predecessor") ? (
          <CellEditor
            label={`Task ${task.id} predecessor`}
            placeholder="Task ID: 12, 12+3, 12SS+4"
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${task.id} predecessor`}
            onEdit={() => handleCellClick(task, "predecessor")}
          >
            {task.predecessor || "-"}
          </EditButton>
        )}
      </td>

      <td style={{ padding: "8px", border: "1px solid #ddd" }}>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            handleIndent(task);
          }}
          disabled={!canIndent}
          title="Indent under previous task"
        >
          Indent
        </button>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            handleOutdent(task);
          }}
          disabled={!canOutdent}
          title="Move up one hierarchy level"
        >
          Outdent
        </button>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            handleDelete(task.id);
          }}
        >
          Delete
        </button>
      </td>
    </tr>
  );
}

export default SortableTaskRow;
