import { useEffect, useId, useRef } from "react";

import Button from "../ui/Button";
import Icon from "../ui/Icon";


function DrawingDialog({
  title,
  eyebrow,
  children,
  actions,
  onClose,
  busy = false,
}) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    closeRef.current?.focus();
    return () => {
      if (previouslyFocused instanceof HTMLElement) {
        previouslyFocused.focus();
      }
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !busy) {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable =
      dialogRef.current?.querySelectorAll(
        "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)"
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

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog drawing-dialog"
        onKeyDown={handleKeyDown}
      >
        <div className="drawing-dialog__header">
          <div>
            {eyebrow && <p>{eyebrow}</p>}
            <h2 id={titleId}>{title}</h2>
          </div>
          <Button
            ref={closeRef}
            size="sm"
            variant="ghost"
            aria-label={`Close ${title}`}
            disabled={busy}
            onClick={onClose}
          >
            <Icon name="x" size={18} />
          </Button>
        </div>
        <div className="drawing-dialog__body">{children}</div>
        {actions && <div className="dialog__actions">{actions}</div>}
      </div>
    </div>
  );
}

export default DrawingDialog;
