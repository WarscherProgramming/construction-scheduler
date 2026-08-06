import { useId, useMemo, useState } from "react";

import DrawingDialog from "../drawings/DrawingDialog";
import Button from "../ui/Button";


const DECISIONS = [
  ["accepted", "Accept"],
  ["needs_review", "Needs further review"],
  ["rejected", "Reject"],
];

// Mirrors the server transition table. The server remains authoritative; this
// only avoids offering a decision that will be refused.
const ALLOWED_TRANSITIONS = {
  proposed: ["accepted", "rejected", "needs_review"],
  needs_review: ["accepted", "rejected"],
  accepted: ["needs_review"],
  rejected: ["needs_review"],
  superseded: [],
};

const SETTLED_STATUSES = ["accepted", "rejected"];


function ReviewAssertionDialog({ assertion, reasonCodes = [], busy, onClose, onSubmit }) {
  const allowed = ALLOWED_TRANSITIONS[assertion.status] || [];
  const [decision, setDecision] = useState(allowed[0] || "needs_review");
  const [reasonCode, setReasonCode] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  // A note is mandatory for rejection, for reversing a settled decision, and
  // whenever the reason is "other".
  const noteRequired = useMemo(
    () =>
      decision === "rejected" ||
      SETTLED_STATUSES.includes(assertion.status) ||
      reasonCode === "other",
    [assertion.status, decision, reasonCode]
  );

  const pending = busy || submitting;

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (noteRequired && !note.trim()) {
      setError("A reviewer note is required for this decision.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        decision,
        reason_code: reasonCode || null,
        reviewer_note: note.trim() || null,
      });
      onClose();
    } catch (requestError) {
      // Preserve recoverable input so the reviewer does not retype the note.
      setError(requestError.message || "Unable to record this review.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Review scope assertion"
      eyebrow="Human review"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={pending || allowed.length === 0}
            type="submit"
            form="assertion-review-form"
          >
            {pending ? "Saving…" : "Record decision"}
          </Button>
        </>
      }
    >
      <form
        id="assertion-review-form"
        className="preconstruction-dialog-form"
        onSubmit={submit}
      >
        <dl className="assertion-review-identity">
          <div>
            <dt>Assertion</dt>
            <dd>{assertion.subject}</dd>
          </div>
          <div>
            <dt>Concept</dt>
            <dd>
              {assertion.concept_name} ({assertion.concept_category_label})
            </dd>
          </div>
          <div>
            <dt>Current decision</dt>
            <dd>{assertion.status_label}</dd>
          </div>
          <div>
            <dt>Evidence</dt>
            <dd>{assertion.evidence_count} cited segment(s)</dd>
          </div>
        </dl>

        {allowed.length === 0 ? (
          <p className="preconstruction-form-error" role="alert">
            This assertion can no longer be reviewed.
          </p>
        ) : (
          <fieldset className="field-group">
            <legend>Decision</legend>
            {DECISIONS.filter(([value]) => allowed.includes(value)).map(
              ([value, label]) => (
                <label key={value} className="assertion-review-option">
                  <input
                    type="radio"
                    name="assertion-decision"
                    value={value}
                    checked={decision === value}
                    onChange={() => setDecision(value)}
                  />
                  <span>{label}</span>
                </label>
              )
            )}
          </fieldset>
        )}

        <label className="field-group">
          <span>Reason</span>
          <select
            value={reasonCode}
            onChange={(event) => setReasonCode(event.target.value)}
          >
            <option value="">No reason selected</option>
            {reasonCodes.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>
            Reviewer note{noteRequired ? " (required)" : " (optional)"}
          </span>
          <textarea
            value={note}
            rows="4"
            maxLength="2000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        <p className="preconstruction-hint">
          Accepting an assertion records a human decision. It remains advisory
          and does not change documents, drawings, schedules, or contracts.
        </p>
        {error && (
          <p id={errorId} className="preconstruction-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </DrawingDialog>
  );
}

export default ReviewAssertionDialog;
