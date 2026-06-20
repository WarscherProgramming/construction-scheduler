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
  handleToggleCollapse,
  formatDate,
  hasChildren,
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
        ☰ {index + 1}
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
            onKeyDown={(event) => {
              if (event.key === "Tab" && !event.shiftKey) {
                event.preventDefault();
                setEditValue((previousValue) => `    ${previousValue}`);
              }

              if (
                event.key === "Backspace" &&
                editValue.startsWith("    ")
              ) {
                event.preventDefault();
                setEditValue((previousValue) => previousValue.substring(4));
              }
            }}
            onBlur={() => handleCellSave(task)}
          />
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
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
            placeholder="1, 1+3, 1SS, 1SS+4"
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
