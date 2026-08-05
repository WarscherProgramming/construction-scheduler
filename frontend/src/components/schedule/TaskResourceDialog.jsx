import { useEffect, useId, useMemo, useRef, useState } from "react";

import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import Icon from "../ui/Icon";


function TaskResourceDialog({ task, displayId, resources, onChanged, onCancel }) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const firstFieldRef = useRef(null);
  const [resourceType, setResourceType] = useState("crew");
  const [resourceId, setResourceId] = useState("");
  const [allocation, setAllocation] = useState("1");
  const [notes, setNotes] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [error, setError] = useState(null);
  const loadAssignments = resources.loadAssignments;
  const isPending = resources.isPending("create-assignment") ||
    resources.isPending("update-assignment") ||
    resources.isPending("delete-assignment");
  const options = useMemo(
    () => (resourceType === "crew" ? resources.crews : resources.equipment)
      .filter((resource) => resource.status === "active"),
    [resourceType, resources.crews, resources.equipment]
  );

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    void loadAssignments(task.id);
    firstFieldRef.current?.focus();
    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [loadAssignments, task.id]);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !isPending) {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = dialogRef.current?.querySelectorAll(
      "select:not(:disabled), input:not(:disabled), textarea:not(:disabled), button:not(:disabled)"
    ) || [];
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const reset = () => {
    setEditingId(null);
    setResourceType("crew");
    setResourceId("");
    setAllocation("1");
    setNotes("");
    setError(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    const amount = Number(allocation);
    if (!Number.isInteger(amount) || amount < 1 || amount > 1_000_000) {
      setError("Enter a whole allocation from 1 to 1000000.");
      return;
    }
    if (!editingId && !resourceId) {
      setError("Select a resource.");
      return;
    }
    const result = editingId
      ? await resources.updateAssignment(task.id, editingId, {
          allocation_amount: amount,
          notes: notes.trim() || null,
        })
      : await resources.createAssignment(task.id, {
          resource_type: resourceType,
          resource_id: Number(resourceId),
          allocation_amount: amount,
          notes: notes.trim() || null,
        });
    if (result) {
      reset();
      await onChanged?.();
    }
  };

  const handleDelete = async () => {
    const assignment = pendingDelete;
    setPendingDelete(null);
    if (!assignment) return;
    const result = await resources.deleteAssignment(task.id, assignment.id);
    if (result) await onChanged?.();
  };

  return (
    <div className="dialog-overlay" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !isPending) onCancel();
    }}>
      <div ref={dialogRef} className="dialog resource-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleKeyDown}>
        <div className="dialog__header">
          <span className="dialog__icon"><Icon name="user" size={20} /></span>
          <div className="dialog__text">
            <h2 id={titleId} className="dialog__title">Task Resources</h2>
            <p className="dialog__message">Task {displayId}: {task.name}</p>
          </div>
        </div>

        <section aria-labelledby={`${titleId}-assigned`}>
          <h3 id={`${titleId}-assigned`}>Assigned resources</h3>
          {resources.isLoadingAssignments ? (
            <p role="status">Loading assignments...</p>
          ) : resources.assignments.length ? (
            <ul className="resource-assignment-list">
              {resources.assignments.map((assignment) => (
                <li key={assignment.id}>
                  <div>
                    <strong>{assignment.resource.name}</strong>
                    <span>{assignment.allocation_amount} {assignment.allocation_unit}</span>
                    {assignment.notes && <small>{assignment.notes}</small>}
                  </div>
                  <div className="resource-inline-actions">
                    <Button size="sm" onClick={() => {
                      setEditingId(assignment.id);
                      setResourceType(assignment.resource.resource_type);
                      setAllocation(String(assignment.allocation_amount));
                      setNotes(assignment.notes || "");
                      setError(null);
                    }}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => setPendingDelete(assignment)}>Delete</Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="resource-empty">No crews or equipment assigned.</p>
          )}
        </section>

        <form className="resource-dialog-form" onSubmit={submit}>
          <h3>{editingId ? "Edit assignment" : "Add assignment"}</h3>
          {!editingId && (
            <>
              <label>Resource type
                <select ref={firstFieldRef} className="field-control" value={resourceType} onChange={(event) => {
                  setResourceType(event.target.value);
                  setResourceId("");
                }}>
                  <option value="crew">Crew</option>
                  <option value="equipment">Equipment</option>
                </select>
              </label>
              <label>Resource
                <select className="field-control" value={resourceId} onChange={(event) => setResourceId(event.target.value)} required>
                  <option value="">Select {resourceType === "crew" ? "crew" : "equipment"}</option>
                  {options.map((resource) => <option key={resource.id} value={resource.id}>{resource.name}</option>)}
                </select>
              </label>
            </>
          )}
          <label>Allocation ({resourceType === "crew" ? "workers" : "units"})
            <input className="field-control" type="number" min="1" max="1000000" step="1" value={allocation} onChange={(event) => setAllocation(event.target.value)} required />
          </label>
          <label>Notes
            <textarea className="field-control" maxLength="1000" value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="dialog__actions">
            {editingId && <Button type="button" onClick={reset} disabled={isPending}>Cancel Edit</Button>}
            <Button type="submit" variant="primary" disabled={isPending || resources.isLoadingAssignments}>{isPending ? "Saving..." : editingId ? "Save Assignment" : "Assign Resource"}</Button>
          </div>
        </form>

        <div className="dialog__actions">
          <Button onClick={onCancel} disabled={isPending}>Close</Button>
        </div>
      </div>
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        destructive
        title="Remove this assignment?"
        message={pendingDelete ? `${pendingDelete.resource.name} will no longer contribute demand to this task.` : ""}
        confirmLabel="Remove"
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}


export default TaskResourceDialog;
