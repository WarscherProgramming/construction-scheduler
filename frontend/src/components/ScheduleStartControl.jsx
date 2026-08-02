import { useState } from "react";

import { parseLocalDateInputValue } from "../utils/date";
import Button from "./ui/Button";
import Card from "./ui/Card";
import ConfirmDialog from "./ui/ConfirmDialog";


function ScheduleStartControl({
  settings,
  taskCount,
  isLoading = false,
  isUpdating = false,
  onUpdate,
}) {
  const [draftDate, setDraftDate] = useState(
    () => settings?.schedule_start_date || ""
  );
  const [error, setError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const applyUpdate = async () => {
    setConfirmOpen(false);
    const result = await onUpdate(draftDate);
    if (!result) setDraftDate(settings?.schedule_start_date || "");
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setError(null);

    if (!parseLocalDateInputValue(draftDate)) {
      setError("Enter a valid Schedule Start Date.");
      return;
    }
    if (draftDate === settings?.schedule_start_date) return;

    if (taskCount > 0) {
      setConfirmOpen(true);
    } else {
      void applyUpdate();
    }
  };

  return (
    <Card title="Schedule Settings" style={{ marginBottom: "var(--space-4)" }}>
      <ConfirmDialog
        open={confirmOpen}
        title="Change Schedule Start Date?"
        message={`This will recalculate ${taskCount} ${
          taskCount === 1 ? "task" : "tasks"
        } without a manual or predecessor anchor.`}
        confirmLabel="Recalculate Schedule"
        confirmDisabled={isUpdating}
        onConfirm={applyUpdate}
        onCancel={() => setConfirmOpen(false)}
      />
      {isLoading && !settings ? (
        <p role="status">Loading schedule settings...</p>
      ) : settings ? (
        <form className="form-stack" noValidate onSubmit={handleSubmit}>
          <div className="field-group">
            <label className="field-label" htmlFor="schedule-start-date">
              Schedule Start Date
            </label>
            <input
              id="schedule-start-date"
              className="field-control"
              type="date"
              required
              value={draftDate}
              disabled={isUpdating}
              aria-describedby={
                error
                  ? "schedule-start-help schedule-start-error"
                  : "schedule-start-help"
              }
              aria-invalid={Boolean(error)}
              onChange={(event) => {
                setDraftDate(event.target.value);
                setError(null);
              }}
            />
            <span id="schedule-start-help" className="field-hint">
              Changing this date recalculates unanchored root tasks.
            </span>
            {error && (
              <span id="schedule-start-error" className="cell-error">
                {error}
              </span>
            )}
          </div>
          <Button
            type="submit"
            variant="primary"
            disabled={
              isUpdating || draftDate === settings.schedule_start_date
            }
            aria-busy={isUpdating}
          >
            {isUpdating ? "Updating..." : "Update Schedule Start"}
          </Button>
        </form>
      ) : (
        <p>Schedule settings are unavailable.</p>
      )}
    </Card>
  );
}

export default ScheduleStartControl;
