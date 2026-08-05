import { useEffect, useId, useRef, useState } from "react";

import { parseLocalDateInputValue } from "../../utils/date";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function CreateLookAheadDialog({
  open,
  dataDate,
  isSubmitting = false,
  serverError,
  onSubmit,
  onCancel,
  onClearError,
}) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);
  const nameRef = useRef(null);
  const [name, setName] = useState(
    () => `Three-Week Look-Ahead - ${dataDate || ""}`
  );
  const [anchorDate, setAnchorDate] = useState(dataDate || "");
  const [windowDays, setWindowDays] = useState("21");
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!open) return undefined;
    const previouslyFocused = document.activeElement;
    window.setTimeout(() => nameRef.current?.focus(), 0);
    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [dataDate, open]);

  if (!open) return null;

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !isSubmitting) {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable =
      dialogRef.current?.querySelectorAll(
        "input:not(:disabled), select:not(:disabled), textarea:not(:disabled), button:not(:disabled)"
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

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (!name.trim()) nextErrors.name = "Enter a look-ahead plan name.";
    if (!parseLocalDateInputValue(anchorDate)) {
      nextErrors.anchorDate = "Enter a valid planning anchor date.";
    }
    if (![7, 14, 21, 28, 35, 42].includes(Number(windowDays))) {
      nextErrors.windowDays = "Select a planning window from 7 to 42 days.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    const result = await onSubmit({
      name: name.trim(),
      description: description.trim() || null,
      anchor_date: anchorDate,
      window_days: Number(windowDays),
    });
    if (result) onCancel();
  };

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        className="dialog look-ahead-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onKeyDown={handleKeyDown}
      >
        <div className="dialog__header">
          <span className="dialog__icon">
            <Icon name="calendar" size={20} />
          </span>
          <div className="dialog__text">
            <h2 id={titleId} className="dialog__title">Create Look-Ahead Plan</h2>
            <p id={descriptionId} className="dialog__message">
              Tasks and dates remain linked to the live schedule. This plan
              stores only short-term readiness and commitment details.
            </p>
          </div>
        </div>
        <form className="form-stack" noValidate onSubmit={handleSubmit}>
          <div className="field-group">
            <label className="field-label" htmlFor={`${titleId}-name`}>Name</label>
            <input
              ref={nameRef}
              id={`${titleId}-name`}
              className="field-control"
              maxLength={120}
              value={name}
              disabled={isSubmitting}
              aria-invalid={Boolean(errors.name)}
              onChange={(event) => {
                setName(event.target.value);
                setErrors((current) => ({ ...current, name: null }));
                onClearError?.();
              }}
            />
            {errors.name && <span className="cell-error" role="alert">{errors.name}</span>}
          </div>
          <div className="look-ahead-dialog-grid">
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-anchor`}>
                Planning Anchor
              </label>
              <input
                id={`${titleId}-anchor`}
                className="field-control"
                type="date"
                value={anchorDate}
                disabled={isSubmitting}
                aria-invalid={Boolean(errors.anchorDate)}
                onChange={(event) => {
                  setAnchorDate(event.target.value);
                  setErrors((current) => ({ ...current, anchorDate: null }));
                }}
              />
              {errors.anchorDate && (
                <span className="cell-error" role="alert">{errors.anchorDate}</span>
              )}
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-duration`}>
                Planning Window
              </label>
              <select
                id={`${titleId}-duration`}
                className="field-control"
                value={windowDays}
                disabled={isSubmitting}
                onChange={(event) => setWindowDays(event.target.value)}
              >
                {[7, 14, 21, 28, 35, 42].map((days) => (
                  <option key={days} value={days}>
                    {days} days{days === 21 ? " (three weeks)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor={`${titleId}-description`}>
              Description <span className="field-optional">Optional</span>
            </label>
            <textarea
              id={`${titleId}-description`}
              className="field-control"
              rows={3}
              maxLength={2000}
              value={description}
              disabled={isSubmitting}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          {serverError && (
            <p className="schedule-baseline-error" role="alert">
              {serverError.message || "Unable to create look-ahead plan."}
            </p>
          )}
          <div className="dialog__actions">
            <Button disabled={isSubmitting} onClick={onCancel}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isSubmitting} aria-busy={isSubmitting}>
              <Icon name="plus" size={16} />
              {isSubmitting ? "Creating..." : "Create Plan"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}


export default CreateLookAheadDialog;
