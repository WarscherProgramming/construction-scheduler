import { useEffect, useRef } from "react";

import Button from "./Button";
import Icon from "./Icon";

/**
 * Accessible confirmation modal.
 *
 * - `role="alertdialog"` + `aria-modal`, labelled by its title and message.
 * - Focus moves to Cancel on open (safe default for destructive actions),
 *   Tab is trapped inside the dialog, and focus returns to the previously
 *   focused element on close.
 * - Escape, the Cancel button, and a backdrop click all invoke `onCancel`.
 * - `destructive` switches the icon/confirm button to danger styling.
 */
function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);
  const cancelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const previouslyFocused = document.activeElement;
    cancelRef.current?.focus();

    return () => {
      if (previouslyFocused instanceof HTMLElement) {
        previouslyFocused.focus();
      }
    };
  }, [open]);

  if (!open) return null;

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onCancel();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable =
      dialogRef.current?.querySelectorAll("button:not(:disabled)") || [];
    if (focusable.length === 0) return;

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

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        className="dialog"
        onKeyDown={handleKeyDown}
      >
        <div className="dialog__header">
          <span
            className={`dialog__icon${
              destructive ? " dialog__icon--danger" : ""
            }`}
          >
            <Icon name={destructive ? "trash" : "info"} size={20} />
          </span>
          <div className="dialog__text">
            <h2 id="confirm-dialog-title" className="dialog__title">
              {title}
            </h2>
            <p id="confirm-dialog-message" className="dialog__message">
              {message}
            </p>
          </div>
        </div>

        <div className="dialog__actions">
          <Button ref={cancelRef} onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "danger" : "primary"}
            onClick={onConfirm}
          >
            {destructive && <Icon name="trash" size={16} />}
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
