import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

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
    cursor: "pointer",
  };

  return (
    <tr
      ref={setNodeRef}
      style={rowStyle}
      onClick={() => setSelectedTaskId(task.id)}
    >
      <td
        style={{
          padding: "8px",
          border: "1px solid #ddd",
          cursor: "grab",
        }}
        {...attributes}
        {...listeners}
      >
        ☰ {task.id}
      </td>

      <td
        onClick={(event) => {
          event.stopPropagation();
          handleCellClick(task, "name");
        }}
        style={{
          padding: "8px",
          border: "1px solid #ddd",
          whiteSpace: "pre",
        }}
      >
        {editingCell?.id === task.id && editingCell.field === "name" ? (
          <input
            autoFocus
            value={editValue}
            onChange={(event) => setEditValue(event.target.value)}
            onBlur={() => handleCellSave(task)}
          />
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              paddingLeft: `${depth * 20}px`,
            }}
          >
            <span style={{ fontWeight: hasChildren ? "600" : "400" }}>
              {task.name}
            </span>

            {hasChildren && (
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  handleToggleCollapse(task);
                }}
                style={{
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: "12px",
                  padding: "0",
                }}
              >
                {task.is_collapsed ? "▶" : "▼"}
              </button>
            )}
          </div>
        )}
      </td>

      <td
        onClick={(event) => {
          event.stopPropagation();
          handleCellClick(task, "duration");
        }}
        style={{ padding: "8px", border: "1px solid #ddd" }}
      >
        {editingCell?.id === task.id && editingCell.field === "duration" ? (
          <input
            autoFocus
            value={editValue}
            onChange={(event) => setEditValue(event.target.value)}
            onBlur={() => handleCellSave(task)}
          />
        ) : (
          task.duration
        )}
      </td>

      <td
        onClick={(event) => {
          event.stopPropagation();
          handleCellClick(task, "manual_start_date");
        }}
        style={{ padding: "8px", border: "1px solid #ddd" }}
      >
        {editingCell?.id === task.id &&
        editingCell.field === "manual_start_date" ? (
          <input
            autoFocus
            type="date"
            value={editValue || ""}
            onChange={(event) => setEditValue(event.target.value)}
            onBlur={() => handleCellSave(task)}
          />
        ) : (
          formatDate(task.start_date)
        )}
      </td>

      <td style={{ padding: "8px", border: "1px solid #ddd" }}>
        {formatDate(task.end_date)}
      </td>

      <td
        onClick={(event) => {
          event.stopPropagation();
          handleCellClick(task, "predecessor");
        }}
        style={{ padding: "8px", border: "1px solid #ddd" }}
      >
        {editingCell?.id === task.id &&
        editingCell.field === "predecessor" ? (
          <input
            autoFocus
            placeholder="Task ID: 12, 12+3, 12SS+4"
            value={editValue}
            onChange={(event) => setEditValue(event.target.value)}
            onBlur={() => handleCellSave(task)}
          />
        ) : (
          task.predecessor || "-"
        )}
      </td>

      <td style={{ padding: "8px", border: "1px solid #ddd" }}>
        <button
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
