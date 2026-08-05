import { useEffect, useId, useRef, useState } from "react";

import {
  formatProgressStatus,
  isValidStatusDate,
} from "../../utils/scheduleProgress";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function TaskProgressDialog({
  task,
  displayId,
  dataDate,
  isSubmitting = false,
  onSubmit,
  onCancel,
}) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);
  const statusRef = useRef(null);
  const reversalCancelRef = useRef(null);
  const [progressStatus, setProgressStatus] = useState(
    task.progress_status || "not_started"
  );
  const [actualStart, setActualStart] = useState(
    task.actual_start_date || ""
  );
  const [actualFinish, setActualFinish] = useState(
    task.actual_finish_date || ""
  );
  const [percentComplete, setPercentComplete] = useState(
    task.percent_complete || ""
  );
  const [remainingDuration, setRemainingDuration] = useState(
    task.remaining_duration ?? task.duration ?? ""
  );
  const [errors, setErrors] = useState({});
  const [confirmingReversal, setConfirmingReversal] = useState(false);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    statusRef.current?.focus();

    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, []);

  useEffect(() => {
    if (confirmingReversal) reversalCancelRef.current?.focus();
  }, [confirmingReversal]);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !isSubmitting) {
      event.stopPropagation();
      if (confirmingReversal) setConfirmingReversal(false);
      else onCancel();
      return;
    }
    if (event.key !== "Tab") return;

    const focusable =
      dialogRef.current?.querySelectorAll(
        "select:not(:disabled), input:not(:disabled), button:not(:disabled)"
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

  const validate = () => {
    const nextErrors = {};

    if (progressStatus === "in_progress") {
      if (!isValidStatusDate(actualStart, dataDate)) {
        nextErrors.actualStart =
          "Enter an Actual Start on or before the Data Date.";
      }
      const percent = Number(percentComplete);
      if (!Number.isInteger(percent) || percent < 1 || percent > 99) {
        nextErrors.percentComplete = "Enter a whole percentage from 1 to 99.";
      }
      const remaining = Number(remainingDuration);
      if (!Number.isInteger(remaining) || remaining < 1 || remaining > 36_500) {
        nextErrors.remainingDuration =
          "Enter 1 to 36500 remaining workdays.";
      }
    }

    if (progressStatus === "completed") {
      if (!isValidStatusDate(actualStart, dataDate)) {
        nextErrors.actualStart =
          "Enter an Actual Start on or before the Data Date.";
      }
      if (!isValidStatusDate(actualFinish, dataDate)) {
        nextErrors.actualFinish =
          "Enter an Actual Finish on or before the Data Date.";
      } else if (actualStart && actualFinish < actualStart) {
        nextErrors.actualFinish = "Actual Finish cannot be before Actual Start.";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const submitProgress = async () => {
    const payload = { progress_status: progressStatus };
    if (progressStatus === "in_progress") {
      Object.assign(payload, {
        actual_start_date: actualStart,
        percent_complete: Number(percentComplete),
        remaining_duration: Number(remainingDuration),
      });
    } else if (progressStatus === "completed") {
      Object.assign(payload, {
        actual_start_date: actualStart,
        actual_finish_date: actualFinish,
      });
    }
    return onSubmit(task.id, payload);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!validate()) return;
    if (
      task.progress_status === "completed" &&
      progressStatus !== "completed" &&
      !confirmingReversal
    ) {
      setConfirmingReversal(true);
      return;
    }
    void submitProgress();
  };

  const describedBy = (field) =>
    errors[field] ? `${titleId}-${field}-error` : undefined;

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        className="dialog schedule-progress-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onKeyDown={handleKeyDown}
      >
        <div className="dialog__header">
          <span className="dialog__icon">
            <Icon name="clipboard-check" size={20} />
          </span>
          <div className="dialog__text">
            <h2 id={titleId} className="dialog__title">
              Update Progress: {task.name}
            </h2>
            <p id={descriptionId} className="dialog__message">
              Task {displayId}. Progress is current through {dataDate}.
            </p>
          </div>
        </div>

        {confirmingReversal ? (
          <div className="schedule-progress-reversal" role="alert">
            <h3>Reverse completed work?</h3>
            <p>
              This correction changes the task to {formatProgressStatus(
                progressStatus
              )} and clears its Actual Finish. Field history is not retained.
            </p>
            <div className="dialog__actions">
              <Button
                ref={reversalCancelRef}
                disabled={isSubmitting}
                onClick={() => setConfirmingReversal(false)}
              >
                Keep Completed
              </Button>
              <Button
                variant="primary"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                onClick={() => void submitProgress()}
              >
                Confirm Correction
              </Button>
            </div>
          </div>
        ) : (
          <form className="form-stack" noValidate onSubmit={handleSubmit}>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-status`}>
                Progress Status
              </label>
              <select
                ref={statusRef}
                id={`${titleId}-status`}
                className="field-control"
                value={progressStatus}
                disabled={isSubmitting}
                onChange={(event) => {
                  setProgressStatus(event.target.value);
                  setErrors({});
                }}
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            {progressStatus === "not_started" && (
              <p className="field-hint">
                Actual dates are cleared, progress returns to 0%, and remaining
                duration resets to {task.duration} workdays.
              </p>
            )}

            {(progressStatus === "in_progress" ||
              progressStatus === "completed") && (
              <div className="field-group">
                <label
                  className="field-label"
                  htmlFor={`${titleId}-actual-start`}
                >
                  Actual Start
                </label>
                <input
                  id={`${titleId}-actual-start`}
                  className="field-control"
                  type="date"
                  value={actualStart}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(errors.actualStart)}
                  aria-describedby={describedBy("actualStart")}
                  onChange={(event) => {
                    setActualStart(event.target.value);
                    setErrors((current) => ({ ...current, actualStart: null }));
                  }}
                />
                {errors.actualStart && (
                  <span
                    id={`${titleId}-actualStart-error`}
                    className="cell-error"
                    role="alert"
                  >
                    {errors.actualStart}
                  </span>
                )}
              </div>
            )}

            {progressStatus === "in_progress" && (
              <div className="schedule-progress-fields">
                <div className="field-group">
                  <label
                    className="field-label"
                    htmlFor={`${titleId}-percent`}
                  >
                    Percent Complete
                  </label>
                  <input
                    id={`${titleId}-percent`}
                    className="field-control"
                    type="number"
                    min="1"
                    max="99"
                    step="1"
                    value={percentComplete}
                    disabled={isSubmitting}
                    aria-invalid={Boolean(errors.percentComplete)}
                    aria-describedby={describedBy("percentComplete")}
                    onChange={(event) => {
                      setPercentComplete(event.target.value);
                      setErrors((current) => ({
                        ...current,
                        percentComplete: null,
                      }));
                    }}
                  />
                  {errors.percentComplete && (
                    <span
                      id={`${titleId}-percentComplete-error`}
                      className="cell-error"
                      role="alert"
                    >
                      {errors.percentComplete}
                    </span>
                  )}
                </div>
                <div className="field-group">
                  <label
                    className="field-label"
                    htmlFor={`${titleId}-remaining`}
                  >
                    Remaining Duration
                  </label>
                  <input
                    id={`${titleId}-remaining`}
                    className="field-control"
                    type="number"
                    min="1"
                    max="36500"
                    step="1"
                    value={remainingDuration}
                    disabled={isSubmitting}
                    aria-invalid={Boolean(errors.remainingDuration)}
                    aria-describedby={describedBy("remainingDuration")}
                    onChange={(event) => {
                      setRemainingDuration(event.target.value);
                      setErrors((current) => ({
                        ...current,
                        remainingDuration: null,
                      }));
                    }}
                  />
                  {errors.remainingDuration && (
                    <span
                      id={`${titleId}-remainingDuration-error`}
                      className="cell-error"
                      role="alert"
                    >
                      {errors.remainingDuration}
                    </span>
                  )}
                </div>
              </div>
            )}

            {progressStatus === "completed" && (
              <div className="field-group">
                <label
                  className="field-label"
                  htmlFor={`${titleId}-actual-finish`}
                >
                  Actual Finish
                </label>
                <input
                  id={`${titleId}-actual-finish`}
                  className="field-control"
                  type="date"
                  value={actualFinish}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(errors.actualFinish)}
                  aria-describedby={describedBy("actualFinish")}
                  onChange={(event) => {
                    setActualFinish(event.target.value);
                    setErrors((current) => ({ ...current, actualFinish: null }));
                  }}
                />
                {errors.actualFinish && (
                  <span
                    id={`${titleId}-actualFinish-error`}
                    className="cell-error"
                    role="alert"
                  >
                    {errors.actualFinish}
                  </span>
                )}
              </div>
            )}

            <div className="dialog__actions">
              <Button disabled={isSubmitting} onClick={onCancel}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
              >
                {isSubmitting ? "Updating..." : "Update Progress"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default TaskProgressDialog;
