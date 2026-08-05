import { useId, useState } from "react";

import DrawingDialog from "../drawings/DrawingDialog";
import LoadingState from "../LoadingState";
import Button from "../ui/Button";
import StatusBadge from "../StatusBadge";


function AddReviewSourceDialog({
  roles,
  existingSources,
  candidates,
  isSearching,
  busy,
  onSearch,
  onAdd,
  onClose,
}) {
  const [sourceType, setSourceType] = useState("document");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState(roles[0]?.value || "drawing");
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const errorId = useId();

  const search = (event) => {
    event.preventDefault();
    setSelected(null);
    void onSearch(sourceType, query.trim());
  };

  const submit = async () => {
    if (!selected) {
      setError("Select a source to add.");
      return;
    }
    setError("");
    try {
      await onAdd({
        source_type: selected.source_type,
        document_id: selected.document_id,
        drawing_revision_id: selected.drawing_revision_id,
        document_role: role,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to add review source.");
    }
  };

  const activeDocumentIds = new Set(existingSources.map((source) => source.document_id));
  return (
    <DrawingDialog
      title="Add Review Source"
      eyebrow="Preconstruction"
      onClose={onClose}
      busy={busy}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={busy || !selected} onClick={submit}>Add Source</Button>
        </>
      }
    >
      <form className="preconstruction-source-search" onSubmit={search}>
        <label className="field-group">
          <span>Source type</span>
          <select
            value={sourceType}
            onChange={(event) => {
              setSourceType(event.target.value);
              setSelected(null);
              setError("");
            }}
          >
            <option value="document">Document</option>
            <option value="drawing_revision">Drawing Revision</option>
          </select>
        </label>
        <label className="field-group preconstruction-source-search__query">
          <span>Search name, type, sheet, title, or revision</span>
          <input value={query} maxLength="200" onChange={(event) => setQuery(event.target.value)} />
        </label>
        <Button type="submit" disabled={isSearching}>Search</Button>
      </form>

      {isSearching ? (
        <LoadingState message="Searching source candidates..." />
      ) : (
        <ul className="preconstruction-candidate-list" role="listbox" aria-label="Source candidates">
          {candidates.map((candidate) => {
            const unavailable = activeDocumentIds.has(candidate.document_id);
            const selectedCandidate = selected?.document_id === candidate.document_id;
            return (
              <li key={`${candidate.source_type}-${candidate.document_id}`}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selectedCandidate}
                  disabled={unavailable}
                  onClick={() => setSelected(candidate)}
                >
                  <span>
                    <strong>{candidate.display_name}</strong>
                    <small>
                      {candidate.sheet_number
                        ? `Revision ${candidate.revision_code}${candidate.is_current_revision ? " · Current" : " · Superseded"}`
                        : candidate.document_type}
                    </small>
                  </span>
                  <StatusBadge value={unavailable ? "Already Added" : candidate.extraction_status} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <label className="field-group">
        <span>Document role</span>
        <select value={role} onChange={(event) => setRole(event.target.value)}>
          {roles.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} ({option.category})
            </option>
          ))}
        </select>
      </label>
      {error && <p id={errorId} className="preconstruction-form-error" role="alert">{error}</p>}
    </DrawingDialog>
  );
}

export default AddReviewSourceDialog;
