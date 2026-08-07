import { useId, useMemo, useState } from "react";

import DrawingDialog from "../drawings/DrawingDialog";
import Button from "../ui/Button";


const REVIEW_DECISIONS = [
  ["accepted", "Accept"],
  ["needs_review", "Needs further review"],
  ["intentional_exclusion", "Intentional exclusion"],
  ["rejected", "Reject"],
];

// Mirrors the server transition table; the server stays authoritative.
const ALLOWED_TRANSITIONS = {
  proposed: ["accepted", "rejected", "needs_review", "intentional_exclusion"],
  needs_review: ["accepted", "rejected", "intentional_exclusion"],
  accepted: ["needs_review"],
  rejected: ["needs_review"],
  intentional_exclusion: ["needs_review"],
  superseded: [],
};
const SETTLED = ["accepted", "rejected", "intentional_exclusion"];
const NOTE_REQUIRED_DECISIONS = ["rejected", "intentional_exclusion"];

const REVIEW_REASONS = [
  ["confirmed_gap", "Confirmed gap"],
  ["confirmed_conflict", "Confirmed conflict"],
  ["intentional_exclusion", "Intentional exclusion"],
  ["covered_elsewhere", "Covered elsewhere"],
  ["duplicate", "Duplicate"],
  ["incorrect_match", "Incorrect match"],
  ["insufficient_evidence", "Insufficient evidence"],
  ["wrong_comparison_type", "Wrong comparison type"],
  ["superseded_source", "Superseded source"],
  ["not_applicable", "Not applicable"],
  ["requires_trade_review", "Requires trade review"],
  ["requires_legal_review", "Requires legal review"],
  ["other", "Other"],
];


export function CreateComparisonPlanDialog({
  comparisonTypes,
  busy,
  onClose,
  onSubmit,
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [comparisonType, setComparisonType] = useState(
    comparisonTypes[0]?.value || "general_scope_coverage"
  );
  const [includeManual, setIncludeManual] = useState(true);
  const [minimumReviewState, setMinimumReviewState] = useState("accepted");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const selected = useMemo(
    () => comparisonTypes.find((item) => item.value === comparisonType),
    [comparisonType, comparisonTypes]
  );
  const pending = busy || submitting;

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (!name.trim()) {
      setError("A comparison plan name is required.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        comparison_type: comparisonType,
        include_manual_assertions: includeManual,
        minimum_review_state: minimumReviewState,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to create this comparison plan.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Create comparison plan"
      eyebrow="Scope comparison"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={pending} type="submit" form="comparison-plan-form">
            {pending ? "Saving…" : "Create plan"}
          </Button>
        </>
      }
    >
      <form id="comparison-plan-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <p className="preconstruction-hint">
          A comparison plan pins which accepted assertions are compared and how.
          The first run locks the plan so results stay reproducible.
        </p>
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
          <span>Comparison type</span>
          <select
            value={comparisonType}
            onChange={(event) => setComparisonType(event.target.value)}
          >
            {comparisonTypes.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        {selected && (
          <p className="preconstruction-hint">
            {selected.description} Requirement roles:{" "}
            {selected.left_roles.join(", ")}. Coverage roles:{" "}
            {selected.right_roles.join(", ")}.
            {selected.notes ? ` ${selected.notes}` : ""}
          </p>
        )}
        <label className="field-group">
          <span>Assertions to compare</span>
          <select
            value={minimumReviewState}
            onChange={(event) => setMinimumReviewState(event.target.value)}
          >
            <option value="accepted">Accepted assertions only</option>
            <option value="accepted_or_needs_review">
              Accepted and needs-review assertions
            </option>
          </select>
        </label>
        <label className="assertion-review-option">
          <input
            type="checkbox"
            checked={includeManual}
            onChange={(event) => setIncludeManual(event.target.checked)}
          />
          <span>Include human-authored assertions</span>
        </label>
        <label className="field-group">
          <span>Description</span>
          <textarea
            value={description}
            rows="3"
            maxLength="2000"
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        {error && (
          <p id={errorId} className="preconstruction-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </DrawingDialog>
  );
}


export function ReviewFindingDialog({ finding, busy, onClose, onSubmit }) {
  const allowed = ALLOWED_TRANSITIONS[finding.status] || [];
  const [decision, setDecision] = useState(allowed[0] || "needs_review");
  const [reasonCode, setReasonCode] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const noteRequired =
    NOTE_REQUIRED_DECISIONS.includes(decision) ||
    SETTLED.includes(finding.status) ||
    reasonCode === "other";
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
      setError(requestError.message || "Unable to record this review.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Review finding"
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
            form="finding-review-form"
          >
            {pending ? "Saving…" : "Record decision"}
          </Button>
        </>
      }
    >
      <form id="finding-review-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <dl className="assertion-review-identity">
          <div>
            <dt>Finding</dt>
            <dd>{finding.title}</dd>
          </div>
          <div>
            <dt>Type and severity</dt>
            <dd>
              {finding.finding_type_label} · {finding.severity_label}
            </dd>
          </div>
          <div>
            <dt>Current decision</dt>
            <dd>{finding.status_label}</dd>
          </div>
          <div>
            <dt>Evidence</dt>
            <dd>{finding.evidence_count} cited segment(s)</dd>
          </div>
        </dl>

        {allowed.length === 0 ? (
          <p className="preconstruction-form-error" role="alert">
            This finding can no longer be reviewed.
          </p>
        ) : (
          <fieldset className="field-group">
            <legend>Decision</legend>
            {REVIEW_DECISIONS.filter(([value]) => allowed.includes(value)).map(
              ([value, label]) => (
                <label key={value} className="assertion-review-option">
                  <input
                    type="radio"
                    name="finding-decision"
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
          <select value={reasonCode} onChange={(event) => setReasonCode(event.target.value)}>
            <option value="">No reason selected</option>
            {REVIEW_REASONS.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Reviewer note{noteRequired ? " (required)" : " (optional)"}</span>
          <textarea
            value={note}
            rows="4"
            maxLength="2000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        <p className="preconstruction-hint">
          Accepting a finding records a human decision. It remains advisory and
          does not create an RFI, change order, procurement action, or contract
          obligation.
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


// The workflow page each action's record is created in. Nothing here posts to
// those endpoints; the button only navigates, so the human uses the one
// canonical creation form for that record type. No draft text is carried in
// the route: the hash router serializes identifiers only, and draft wording
// does not belong in a URL.
const ACTION_WORKFLOW_PAGES = {
  rfi: ["rfis", "RFIs"],
  change_order: ["changeOrders", "Change Orders"],
  submittal: ["submittals", "Submittals"],
};


export function RaiseFollowUpDialog({
  finding,
  projectId,
  action,
  draft,
  busy,
  onClose,
  onSubmit,
  onNavigate,
}) {
  const [title, setTitle] = useState(draft?.draft_title || "");
  const [body, setBody] = useState(draft?.draft_body || "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const pending = busy || submitting;
  const workflow = ACTION_WORKFLOW_PAGES[action?.value];

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (!title.trim()) {
      setError("A draft title is required.");
      return;
    }
    if (!body.trim()) {
      setError("A draft body is required.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        action_type: action.value,
        draft_title: title.trim(),
        draft_body: body,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to raise this follow-up.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title={`Raise ${action?.label || "follow-up"}`}
      eyebrow="Follow-up action"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={pending}
            type="submit"
            form="follow-up-raise-form"
          >
            {pending ? "Saving…" : "Save follow-up"}
          </Button>
        </>
      }
    >
      <form id="follow-up-raise-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <dl className="assertion-review-identity">
          <div>
            <dt>Finding</dt>
            <dd>{finding.title}</dd>
          </div>
          <div>
            <dt>Type and severity</dt>
            <dd>{finding.finding_type_label} · {finding.severity_label}</dd>
          </div>
          <div>
            <dt>Action</dt>
            <dd>{action?.label}</dd>
          </div>
        </dl>

        <label className="field-group">
          <span>Draft title</span>
          <input
            value={title}
            maxLength="200"
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label className="field-group">
          <span>Draft text</span>
          <textarea
            value={body}
            rows="12"
            maxLength="4000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setBody(event.target.value)}
          />
        </label>

        <p className="preconstruction-hint">
          {action?.guidance} Saving this records your intent only. FieldFlow
          creates no record for you and sends nothing to anyone.
        </p>

        {workflow && (
          <p className="preconstruction-hint">
            Save this draft first, then copy the wording into the record.
            <Button
              onClick={() => onNavigate(workflow[0], projectId)}
              disabled={pending}
            >
              Open {workflow[1]}
            </Button>
          </p>
        )}

        {error && (
          <p id={errorId} className="preconstruction-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </DrawingDialog>
  );
}


export function LinkFollowUpDialog({
  followUp,
  targetType,
  busy,
  onClose,
  onSubmit,
}) {
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const pending = busy || submitting;

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    const parsed = Number(targetId);
    if (!Number.isInteger(parsed) || parsed < 1) {
      setError("Enter the numeric identifier of the record you created.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({ target_type: targetType, target_id: parsed });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to link this record.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Link existing record"
      eyebrow="Follow-up action"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={pending}
            type="submit"
            form="follow-up-link-form"
          >
            {pending ? "Saving…" : "Link record"}
          </Button>
        </>
      }
    >
      <form id="follow-up-link-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <dl className="assertion-review-identity">
          <div>
            <dt>Follow-up</dt>
            <dd>{followUp.draft_title}</dd>
          </div>
          <div>
            <dt>Action</dt>
            <dd>{followUp.action_label}</dd>
          </div>
        </dl>

        <label className="field-group">
          <span>Record identifier</span>
          <input
            value={targetId}
            inputMode="numeric"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setTargetId(event.target.value)}
          />
        </label>

        <p className="preconstruction-hint">
          The record must already exist in this project and must be a{" "}
          {followUp.action_label} record. Linking records the connection only and
          changes nothing about that record.
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


export function CloseFollowUpDialog({ followUp, busy, onClose, onSubmit }) {
  const [status, setStatus] = useState("completed");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const pending = busy || submitting;
  const noteRequired = status === "cancelled";

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (noteRequired && !note.trim()) {
      setError("A note is required when cancelling a follow-up.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({ status, closure_note: note.trim() || null });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to close this follow-up.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Close follow-up"
      eyebrow="Follow-up action"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={pending}
            type="submit"
            form="follow-up-close-form"
          >
            {pending ? "Saving…" : "Close follow-up"}
          </Button>
        </>
      }
    >
      <form id="follow-up-close-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <dl className="assertion-review-identity">
          <div>
            <dt>Follow-up</dt>
            <dd>{followUp.draft_title}</dd>
          </div>
          <div>
            <dt>Current status</dt>
            <dd>{followUp.status_label}</dd>
          </div>
        </dl>

        <fieldset className="field-group">
          <legend>Outcome</legend>
          {[["completed", "Completed"], ["cancelled", "Cancelled"]].map(
            ([value, label]) => (
              <label key={value} className="assertion-review-option">
                <input
                  type="radio"
                  name="follow-up-status"
                  value={value}
                  checked={status === value}
                  onChange={() => setStatus(value)}
                />
                <span>{label}</span>
              </label>
            )
          )}
        </fieldset>

        <label className="field-group">
          <span>Closing note{noteRequired ? " (required)" : " (optional)"}</span>
          <textarea
            value={note}
            rows="4"
            maxLength="2000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        <p className="preconstruction-hint">
          Closing is final. A closed follow-up is never reopened and is kept as
          history.
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


export function CreateManualFindingDialog({
  findings,
  assertions,
  busy,
  onClose,
  onSubmit,
}) {
  const [findingType, setFindingType] = useState("missing_coverage");
  const [severity, setSeverity] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [rationale, setRationale] = useState("");
  const [selectedAssertions, setSelectedAssertions] = useState([]);
  const [selectedEvidence, setSelectedEvidence] = useState([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const pending = busy || submitting;
  const evidenceOptions = useMemo(
    () =>
      assertions
        .filter((item) => selectedAssertions.some((link) => link.id === item.id))
        .flatMap((item) =>
          (item.evidence || []).map((evidence) => ({
            ...evidence,
            assertionSubject: item.subject,
          }))
        ),
    [assertions, selectedAssertions]
  );

  const toggleAssertion = (assertion, side) => {
    setSelectedAssertions((current) => {
      const existing = current.find((item) => item.id === assertion.id);
      if (existing) return current.filter((item) => item.id !== assertion.id);
      return [...current, { id: assertion.id, side }];
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (!title.trim()) return setError("A title is required.");
    if (selectedAssertions.length === 0) {
      return setError("Link at least one accepted assertion.");
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        finding_type: findingType,
        severity: severity || null,
        title: title.trim(),
        summary: summary.trim() || null,
        rationale: rationale.trim() || null,
        assertions: selectedAssertions.map((item) => ({
          assertion_id: item.id,
          side: item.side,
        })),
        evidence_ids: selectedEvidence,
        reviewer_note: note.trim() || null,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to create this finding.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Add a human-authored finding"
      eyebrow="Manual scope comparison"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={pending} type="submit" form="manual-finding-form">
            {pending ? "Saving…" : "Create finding"}
          </Button>
        </>
      }
    >
      <form id="manual-finding-form" className="preconstruction-dialog-form" onSubmit={submit}>
        <p className="preconstruction-hint">
          This finding is authored by you, not produced by comparison or a
          model. It is recorded as accepted with your name on the review history.
        </p>

        <div className="assertion-form-grid">
          <label className="field-group">
            <span>Finding type</span>
            <select
              value={findingType}
              onChange={(event) => setFindingType(event.target.value)}
            >
              {findings.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="field-group">
            <span>Severity</span>
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="">Use the documented default</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="informational">Informational</option>
            </select>
          </label>
        </div>

        <label className="field-group">
          <span>Title</span>
          <input
            value={title}
            maxLength="200"
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="field-group">
          <span>Summary</span>
          <textarea
            value={summary}
            rows="2"
            maxLength="600"
            onChange={(event) => setSummary(event.target.value)}
          />
        </label>
        <label className="field-group">
          <span>Rationale</span>
          <textarea
            value={rationale}
            rows="3"
            maxLength="2000"
            onChange={(event) => setRationale(event.target.value)}
          />
        </label>

        <fieldset className="field-group">
          <legend>Linked assertions</legend>
          {assertions.length === 0 ? (
            <p className="preconstruction-hint">
              No accepted assertions are available to link.
            </p>
          ) : (
            <ul className="finding-assertion-picker">
              {assertions.map((item) => (
                <li key={item.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedAssertions.some((link) => link.id === item.id)}
                      onChange={() => toggleAssertion(item, "requirement")}
                    />
                    <span>
                      {item.subject} — {item.source?.display_name || "Source unavailable"}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        {evidenceOptions.length > 0 && (
          <fieldset className="field-group">
            <legend>Evidence</legend>
            <ul className="assertion-evidence-picker">
              {evidenceOptions.map((item) => (
                <li key={item.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedEvidence.includes(item.id)}
                      onChange={() =>
                        setSelectedEvidence((current) =>
                          current.includes(item.id)
                            ? current.filter((value) => value !== item.id)
                            : [...current, item.id]
                        )
                      }
                    />
                    <span>
                      Page {item.page_number}, segment {item.segment_index}
                    </span>
                  </label>
                  <p className="assertion-evidence-preview">
                    {item.excerpt.slice(0, 200)}
                  </p>
                </li>
              ))}
            </ul>
          </fieldset>
        )}

        <label className="field-group">
          <span>Note</span>
          <textarea
            value={note}
            rows="2"
            maxLength="2000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        {error && (
          <p id={errorId} className="preconstruction-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </DrawingDialog>
  );
}
