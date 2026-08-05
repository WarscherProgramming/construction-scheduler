import { useEffect, useId, useRef, useState } from "react";

import { formatDisplayDate } from "../../utils/date";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";


function ResourceAvailabilityDialog({ resource, resourceType, resources, onChanged, onCancel }) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const [editing, setEditing] = useState(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [capacity, setCapacity] = useState(String(resource.default_capacity));
  const [notes, setNotes] = useState("");
  const [error, setError] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const loadAvailability = resources.loadAvailability;
  const pending = resources.isPending("create-availability") ||
    resources.isPending("update-availability") ||
    resources.isPending("delete-availability");

  useEffect(() => {
    void loadAvailability(resourceType, resource.id);
  }, [loadAvailability, resource.id, resourceType]);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !pending) {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = dialogRef.current?.querySelectorAll(
      "input:not(:disabled), textarea:not(:disabled), button:not(:disabled)"
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
    setEditing(null);
    setStartDate("");
    setEndDate("");
    setCapacity(String(resource.default_capacity));
    setNotes("");
    setError(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    const nextCapacity = Number(capacity);
    if (!startDate || !endDate || endDate < startDate) {
      setError("Select a valid inclusive date range.");
      return;
    }
    if (!Number.isInteger(nextCapacity) || nextCapacity < 0 || nextCapacity > 1_000_000) {
      setError("Enter a whole capacity from 0 to 1000000.");
      return;
    }
    const payload = {
      start_date: startDate,
      end_date: endDate,
      capacity: nextCapacity,
      notes: notes.trim() || null,
    };
    const result = editing
      ? await resources.updateAvailability(resourceType, resource.id, editing.id, payload)
      : await resources.createAvailability(resourceType, resource.id, payload);
    if (result) {
      reset();
      await onChanged?.();
    }
  };

  const remove = async () => {
    const row = pendingDelete;
    setPendingDelete(null);
    if (!row) return;
    const result = await resources.deleteAvailability(resourceType, resource.id, row.id);
    if (result) await onChanged?.();
  };

  return (
    <div className="dialog-overlay" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !pending) onCancel();
    }}>
      <div ref={dialogRef} className="dialog resource-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleKeyDown}>
        <div className="dialog__text">
          <h2 id={titleId} className="dialog__title">Resource Availability</h2>
          <p className="dialog__message">{resource.name} defaults to {resource.default_capacity} {resource.capacity_unit} on workdays. Capacity 0 marks it unavailable.</p>
        </div>
        <section aria-label="Availability overrides">
          {resources.isLoadingAvailability ? <p role="status">Loading availability...</p> : resources.availability.length ? (
            <ul className="resource-availability-list">
              {resources.availability.map((row) => (
                <li key={row.id}>
                  <div><strong>{formatDisplayDate(row.start_date)} to {formatDisplayDate(row.end_date)}</strong><span>{row.capacity} {resource.capacity_unit}{row.capacity === 0 ? " - Unavailable" : ""}</span>{row.notes && <small>{row.notes}</small>}</div>
                  <div className="resource-inline-actions">
                    <Button size="sm" onClick={() => {
                      setEditing(row);
                      setStartDate(row.start_date);
                      setEndDate(row.end_date);
                      setCapacity(String(row.capacity));
                      setNotes(row.notes || "");
                    }}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => setPendingDelete(row)}>Delete</Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : <p className="resource-empty">No dated overrides. Default capacity applies.</p>}
        </section>
        {resource.status === "active" ? <form className="resource-dialog-form" onSubmit={submit}>
          <h3>{editing ? "Edit override" : "Add override"}</h3>
          <div className="resource-form-grid">
            <label>Start date<input className="field-control" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required /></label>
            <label>End date<input className="field-control" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} required /></label>
            <label>Capacity<input className="field-control" type="number" min="0" max="1000000" step="1" value={capacity} onChange={(event) => setCapacity(event.target.value)} required /></label>
          </div>
          <label>Notes<textarea className="field-control" maxLength="1000" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="dialog__actions">
            {editing && <Button type="button" onClick={reset}>Cancel Edit</Button>}
            <Button type="submit" variant="primary" disabled={pending}>{pending ? "Saving..." : editing ? "Save Override" : "Add Override"}</Button>
          </div>
        </form> : <p className="resource-empty">Archived resources retain historical availability, but overrides cannot be changed.</p>}
        <div className="dialog__actions"><Button onClick={onCancel} disabled={pending}>Close</Button></div>
      </div>
      <ConfirmDialog open={Boolean(pendingDelete)} destructive title="Delete this availability override?" message="The resource's default capacity will apply for these dates." confirmLabel="Delete" onConfirm={remove} onCancel={() => setPendingDelete(null)} />
    </div>
  );
}


export default ResourceAvailabilityDialog;
