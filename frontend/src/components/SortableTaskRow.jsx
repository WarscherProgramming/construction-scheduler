import { useRef } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import Icon from "./ui/Icon";


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
      onSave();
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
      onChange={(event) => {
        skipBlurSave.current = false;
        onChange(event.target.value);
      }}
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
      onClick={onEdit}
      style={style}
    >
      {children}
    </button>
  );
}

function SortableTaskRow({
  task,
  index,
  displayId,
  displayPredecessor,
  selectedTaskId,
  setSelectedTaskId,
  editingCell,
  editValue,
  setEditValue,
  handleCellClick,
  handleCellSave,
  handleCellCancel,
  handleDelete,
  handleToggleCollapse,
  formatDate,
  hasChildren,
  depth,
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
    "--schedule-row-bg":
      selectedTaskId === task.id
        ? "#e0f2fe"
        : index % 2 === 0
          ? "#ffffff"
          : "#f9fafb",
    background: "var(--schedule-row-bg)",
  };

  const isEditing = (field) =>
    editingCell?.id === task.id && editingCell.field === field;

  return (
    <tr
      ref={setNodeRef}
      style={rowStyle}
      className={
        selectedTaskId === task.id ? "schedule-row--selected" : undefined
      }
      onClick={() => setSelectedTaskId(task.id)}
    >
      <td className="schedule-sticky-column schedule-sticky-0">
        <button
          type="button"
          className="schedule-icon-button schedule-drag-handle"
          aria-label={`Reorder schedule task ${displayId}: ${task.name}`}
          title="Drag to reorder. Use Space and arrow keys with a keyboard."
          onClick={(event) => event.stopPropagation()}
          {...attributes}
          {...listeners}
        >
          <span className="schedule-drag-lines" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>{displayId}</span>
        </button>
      </td>

      <td className="schedule-sticky-column schedule-sticky-1">
        {isEditing("name") ? (
          <CellEditor
            label={`Task ${displayId} name`}
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
              label={`task ${displayId} name`}
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
                title={task.is_collapsed ? "Expand" : "Collapse"}
                onClick={(event) => {
                  event.stopPropagation();
                  handleToggleCollapse(task);
                }}
              >
                <Icon
                  name={task.is_collapsed ? "chevron-right" : "chevron-down"}
                  size={18}
                />
              </button>
            )}
          </div>
        )}
      </td>

      <td>
        {isEditing("duration") ? (
          <CellEditor
            label={`Task ${displayId} duration`}
            type="number"
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${displayId} duration`}
            onEdit={() => handleCellClick(task, "duration")}
          >
            {task.duration}
          </EditButton>
        )}
      </td>

      <td>
        {isEditing("manual_start_date") ? (
          <CellEditor
            label={`Task ${displayId} start date`}
            type="date"
            value={editValue || ""}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${displayId} start date`}
            onEdit={() => handleCellClick(task, "manual_start_date")}
          >
            {formatDate(task.start_date)}
          </EditButton>
        )}
      </td>

      <td>
        {formatDate(task.end_date)}
      </td>

      <td>
        {isEditing("predecessor") ? (
          <CellEditor
            label={`Task ${displayId} predecessor`}
            placeholder="Schedule ID: 1, 1+3, 1SS+4"
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
          />
        ) : (
          <EditButton
            label={`task ${displayId} predecessor`}
            onEdit={() => handleCellClick(task, "predecessor")}
          >
            {displayPredecessor || "-"}
          </EditButton>
        )}
      </td>

      <td>
        <button
          type="button"
          className="schedule-icon-button schedule-icon-button--danger"
          aria-label="Delete"
          title={`Delete ${task.name}`}
          onClick={(event) => {
            event.stopPropagation();
            handleDelete(task.id);
          }}
        >
          <Icon name="trash" size={17} />
        </button>
      </td>
    </tr>
  );
}

export default SortableTaskRow;
