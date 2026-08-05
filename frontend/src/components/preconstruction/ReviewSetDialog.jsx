import { useId, useState } from "react";

import DrawingDialog from "../drawings/DrawingDialog";
import Button from "../ui/Button";


const PURPOSES = [
  ["bid_scope_review", "Bid Scope Review"],
  ["subcontract_scope_review", "Subcontract Scope Review"],
  ["procurement_review", "Procurement Review"],
  ["submittal_coverage_review", "Submittal Coverage Review"],
  ["revision_impact_review", "Revision Impact Review"],
  ["general_scope_review", "General Scope Review"],
];


function ReviewSetDialog({ reviewSet, busy, onClose, onSubmit }) {
  const [name, setName] = useState(reviewSet?.name || "");
  const [description, setDescription] = useState(reviewSet?.description || "");
  const [purpose, setPurpose] = useState(reviewSet?.purpose || "general_scope_review");
  const [error, setError] = useState("");
  const errorId = useId();

  const submit = async (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Review set name is required.");
      return;
    }
    setError("");
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        purpose,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to save review set.");
    }
  };

  return (
    <DrawingDialog
      title={reviewSet ? "Edit Review Set" : "Create Review Set"}
      eyebrow="Preconstruction"
      onClose={onClose}
      busy={busy}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={busy} type="submit" form="review-set-form">
            {reviewSet ? "Save Changes" : "Create Review Set"}
          </Button>
        </>
      }
    >
      <form id="review-set-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <label className="field-group">
          <span>Name</span>
          <input
            autoFocus
            value={name}
            maxLength="120"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="field-group">
          <span>Purpose</span>
          <select value={purpose} onChange={(event) => setPurpose(event.target.value)}>
            {PURPOSES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="field-group">
          <span>Description</span>
          <textarea
            value={description}
            maxLength="2000"
            rows="4"
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        {error && <p id={errorId} className="preconstruction-form-error" role="alert">{error}</p>}
      </form>
    </DrawingDialog>
  );
}

export default ReviewSetDialog;
