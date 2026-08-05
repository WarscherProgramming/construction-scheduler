import { useState } from "react";

import { parseLocalDateInputValue } from "../utils/date";
import Button from "./ui/Button";
import Card from "./ui/Card";
import ConfirmDialog from "./ui/ConfirmDialog";


function ScheduleStartControl({
  settings,
  taskCount,
  statusedTaskCount = 0,
  isLoading = false,
  isUpdating = false,
  onUpdate,
  onUpdateDataDate = async () => undefined,
}) {
  const [draftDate, setDraftDate] = useState(
    () => settings?.schedule_start_date || ""
  );
  const [draftDataDate, setDraftDataDate] = useState(
    () => settings?.data_date || ""
  );
  const [error, setError] = useState(null);
  const [dataDateError, setDataDateError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [dataDateConfirmOpen, setDataDateConfirmOpen] = useState(false);
  const [pendingField, setPendingField] = useState(null);

  const applyUpdate = async () => {
    setConfirmOpen(false);
    setPendingField("schedule_start_date");
    const result = await onUpdate(draftDate);
    if (!result) {
      setDraftDate(settings?.schedule_start_date || "");
      setPendingField(null);
    }
  };

  const applyDataDateUpdate = async () => {
    setDataDateConfirmOpen(false);
    setPendingField("data_date");
    const result = await onUpdateDataDate(draftDataDate);
    if (!result) {
      setDraftDataDate(settings?.data_date || "");
      setPendingField(null);
    }
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

  const handleDataDateSubmit = (event) => {
    event.preventDefault();
    setDataDateError(null);

    if (!parseLocalDateInputValue(draftDataDate)) {
      setDataDateError("Enter a valid Data Date.");
      return;
    }
    if (draftDataDate === settings?.data_date) return;

    if (statusedTaskCount > 0) {
      setDataDateConfirmOpen(true);
    } else {
      void applyDataDateUpdate();
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
      <ConfirmDialog
        open={dataDateConfirmOpen}
        title="Change Data Date?"
        message={`This will recalculate forecast work for ${statusedTaskCount} statused ${
          statusedTaskCount === 1 ? "task" : "tasks"
        }. Recorded actual dates and progress remain unchanged.`}
        confirmLabel="Update Data Date"
        confirmDisabled={isUpdating}
        onConfirm={applyDataDateUpdate}
        onCancel={() => setDataDateConfirmOpen(false)}
      />
      {isLoading && !settings ? (
        <p role="status">Loading schedule settings...</p>
      ) : settings ? (
        <div className="schedule-settings-forms">
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
                <span
                  id="schedule-start-error"
                  className="cell-error"
                  role="alert"
                >
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
              aria-busy={
                isUpdating && pendingField === "schedule_start_date"
              }
            >
              {isUpdating && pendingField === "schedule_start_date"
                ? "Updating..."
                : "Update Schedule Start"}
            </Button>
          </form>

          <form
            className="form-stack schedule-data-date-form"
            noValidate
            onSubmit={handleDataDateSubmit}
          >
            <div className="field-group">
              <label className="field-label" htmlFor="schedule-data-date">
                Data Date
              </label>
              <input
                id="schedule-data-date"
                className="field-control"
                type="date"
                required
                value={draftDataDate}
                disabled={isUpdating}
                aria-describedby={
                  dataDateError
                    ? "schedule-data-date-help schedule-data-date-error"
                    : "schedule-data-date-help"
                }
                aria-invalid={Boolean(dataDateError)}
                onChange={(event) => {
                  setDraftDataDate(event.target.value);
                  setDataDateError(null);
                }}
              />
              <span id="schedule-data-date-help" className="field-hint">
                Progress is current through this date; incomplete work is
                forecast from this boundary.
              </span>
              {dataDateError && (
                <span
                  id="schedule-data-date-error"
                  className="cell-error"
                  role="alert"
                >
                  {dataDateError}
                </span>
              )}
            </div>
            <Button
              type="submit"
              variant="primary"
              disabled={isUpdating || draftDataDate === settings.data_date}
              aria-busy={isUpdating && pendingField === "data_date"}
            >
              {isUpdating && pendingField === "data_date"
                ? "Updating..."
                : "Update Data Date"}
            </Button>
          </form>
        </div>
      ) : (
        <p>Schedule settings are unavailable.</p>
      )}
    </Card>
  );
}

export default ScheduleStartControl;
