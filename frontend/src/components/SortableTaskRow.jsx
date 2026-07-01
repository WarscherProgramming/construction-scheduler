import { useId, useRef, useState } from "react";
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
  validate,
}) {
  const skipBlurSave = useRef(false);
  const [error, setError] = useState(null);
  const errorId = useId();

  // Returns true when the value passed validation and was saved; on failure
  // the editor stays open with an inline message next to the cell.
  const trySave = () => {
    const message = validate ? validate(value) : null;

    if (message) {
      setError(message);
      return false;
    }

    onSave();
    return true;
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      skipBlurSave.current = trySave();
    }

    if (event.key === "Escape") {
      event.preventDefault();
      skipBlurSave.current = true;
      onCancel();
    }
  };

  return (
    <>
      <input
        autoFocus
        aria-label={label}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`schedule-cell-input${
          error ? " schedule-cell-input--invalid" : ""
        }`}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(event) => {
          skipBlurSave.current = false;
          setError(null);
          onChange(event.target.value);
        }}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (!skipBlurSave.current) trySave();
        }}
      />
      {error && (
        <span id={errorId} className="cell-error" role="alert">
          {error}
        </span>
      )}
    </>
  );
}

function EditButton({ label, children, onEdit, style, navProps }) {
  return (
    <button
      type="button"
      className="schedule-cell-button"
      aria-label={`Edit ${label}`}
      onClick={onEdit}
      style={style}
      {...navProps}
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
  validateCell,
  focusedField = null,
  onCellNavigate,
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

  // Roving grid cursor: only the focused cell is in the tab order; arrow and
  // Tab handling live in the parent so the cursor can cross rows.
  const cellNavProps = (field) =>
    onCellNavigate
      ? {
          tabIndex: focusedField === field ? 0 : -1,
          "data-cell": `${index}:${field}`,
          onKeyDown: (event) => onCellNavigate(event, index, field),
        }
      : undefined;

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
            title={
              task.is_critical
                ? "Critical path — 0 workdays of float"
                : task.total_float != null
                  ? `Total float: ${task.total_float} workdays`
                  : undefined
            }
          >
            {task.is_critical && (
              <span className="critical-flag">
                <span className="visually-hidden">Critical path task.</span>
              </span>
            )}
            <EditButton
              label={`task ${displayId} name`}
              onEdit={() => handleCellClick(task, "name")}
              style={{
                flex: 1,
                fontWeight: hasChildren ? "600" : "400",
              }}
              navProps={cellNavProps("name")}
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
            validate={
              validateCell ? (value) => validateCell("duration", value) : undefined
            }
          />
        ) : (
          <EditButton
            label={`task ${displayId} duration`}
            onEdit={() => handleCellClick(task, "duration")}
            navProps={cellNavProps("duration")}
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
            navProps={cellNavProps("manual_start_date")}
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
            placeholder="Schedule ID: 2, 1.2+3, 2SS+4"
            value={editValue}
            onChange={setEditValue}
            onSave={() => handleCellSave(task)}
            onCancel={handleCellCancel}
            validate={
              validateCell
                ? (value) => validateCell("predecessor", value)
                : undefined
            }
          />
        ) : (
          <EditButton
            label={`task ${displayId} predecessor`}
            onEdit={() => handleCellClick(task, "predecessor")}
            navProps={cellNavProps("predecessor")}
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
