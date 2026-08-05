import { useEffect, useId, useRef, useState } from "react";

import { formatDisplayDate } from "../../utils/date";
import Button from "../ui/Button";


const CATEGORIES = [
  ["predecessor_work", "Predecessor Work"],
  ["design_information", "Design Information"],
  ["submittal", "Submittal"],
  ["material", "Material"],
  ["labor", "Labor"],
  ["equipment", "Equipment"],
  ["access", "Access"],
  ["inspection", "Inspection"],
  ["permit", "Permit"],
  ["owner_decision", "Owner Decision"],
  ["safety", "Safety"],
  ["weather", "Weather"],
  ["other", "Other"],
];


function LookAheadItemDialog({
  item,
  companies,
  isCandidate = false,
  isSubmitting = false,
  onSubmit,
  onCancel,
}) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const statusRef = useRef(null);
  const [readiness, setReadiness] = useState(item.readiness_status || "unreviewed");
  const [companyId, setCompanyId] = useState(item.responsible_company?.id || "");
  const [category, setCategory] = useState(item.constraint_category || "");
  const [blockingReason, setBlockingReason] = useState(item.blocking_reason || "");
  const [constraintOwner, setConstraintOwner] = useState(item.constraint_owner || "");
  const [targetDate, setTargetDate] = useState(item.target_resolution_date || "");
  const [commitment, setCommitment] = useState(item.commitment_note || "");
  const [manualIncluded, setManualIncluded] = useState(
    isCandidate || item.manually_included || false
  );
  const [manualExcluded, setManualExcluded] = useState(item.manually_excluded || false);
  const [overrideReason, setOverrideReason] = useState(item.override_reason || "");
  const [error, setError] = useState(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    statusRef.current?.focus();
    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !isSubmitting) {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable =
      dialogRef.current?.querySelectorAll(
        "select:not(:disabled), input:not(:disabled), textarea:not(:disabled), button:not(:disabled)"
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
    if (manualIncluded && manualExcluded) {
      setError("Choose either manual inclusion or exclusion, not both.");
      return;
    }
    const result = await onSubmit(item.task_id, {
      readiness_status: readiness,
      responsible_company_id: companyId ? Number(companyId) : null,
      constraint_category: category || null,
      blocking_reason: blockingReason.trim() || null,
      constraint_owner: constraintOwner.trim() || null,
      target_resolution_date: targetDate || null,
      commitment_note: commitment.trim() || null,
      manually_included: manualIncluded,
      manually_excluded: manualExcluded,
      override_reason: overrideReason.trim() || null,
    });
    if (result) onCancel();
  };

  return (
    <div className="dialog-overlay">
      <div
        ref={dialogRef}
        className="dialog look-ahead-item-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
      >
        <div className="dialog__header">
          <div className="dialog__text">
            <h2 id={titleId} className="dialog__title">
              {isCandidate ? "Include Task" : "Edit Look-Ahead Item"}: {item.name || `Task ${item.task_id}`}
            </h2>
            <p className="dialog__message">
              {item.wbs ? `Task ${item.wbs}. ` : ""}
              Forecast {formatDisplayDate(item.start_date)} to {formatDisplayDate(item.end_date)}.
              Schedule dates and progress are read-only here.
            </p>
          </div>
        </div>
        <form className="form-stack" noValidate onSubmit={handleSubmit}>
          <div className="look-ahead-dialog-grid">
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-readiness`}>Readiness</label>
              <select ref={statusRef} id={`${titleId}-readiness`} className="field-control" value={readiness} disabled={isSubmitting} onChange={(event) => setReadiness(event.target.value)}>
                <option value="unreviewed">Unreviewed</option>
                <option value="ready">Ready</option>
                <option value="at_risk">At Risk</option>
                <option value="blocked">Blocked</option>
                <option value="committed">Committed</option>
                <option value="complete">Complete</option>
              </select>
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-company`}>Responsible Company</label>
              <select id={`${titleId}-company`} className="field-control" value={companyId} disabled={isSubmitting} onChange={(event) => setCompanyId(event.target.value)}>
                <option value="">Unassigned</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}{company.trade ? ` - ${company.trade}` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-category`}>Blocker Category</label>
              <select id={`${titleId}-category`} className="field-control" value={category} disabled={isSubmitting} onChange={(event) => setCategory(event.target.value)}>
                <option value="">None</option>
                {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-target`}>Target Resolution</label>
              <input id={`${titleId}-target`} className="field-control" type="date" value={targetDate} disabled={isSubmitting} onChange={(event) => setTargetDate(event.target.value)} />
            </div>
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor={`${titleId}-owner`}>Constraint Owner</label>
            <input id={`${titleId}-owner`} className="field-control" maxLength={255} value={constraintOwner} disabled={isSubmitting} onChange={(event) => setConstraintOwner(event.target.value)} />
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor={`${titleId}-blocker`}>Blocking Reason</label>
            <textarea id={`${titleId}-blocker`} className="field-control" rows={3} maxLength={2000} value={blockingReason} disabled={isSubmitting} onChange={(event) => setBlockingReason(event.target.value)} />
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor={`${titleId}-commitment`}>Commitment Note</label>
            <textarea id={`${titleId}-commitment`} className="field-control" rows={3} maxLength={2000} value={commitment} disabled={isSubmitting} onChange={(event) => setCommitment(event.target.value)} />
          </div>
          <fieldset className="look-ahead-manual-controls">
            <legend>Planning Window Override</legend>
            <label><input type="checkbox" checked={manualIncluded} disabled={isSubmitting || isCandidate} onChange={(event) => { setManualIncluded(event.target.checked); if (event.target.checked) setManualExcluded(false); }} /> Manually include</label>
            <label><input type="checkbox" checked={manualExcluded} disabled={isSubmitting || isCandidate} onChange={(event) => { setManualExcluded(event.target.checked); if (event.target.checked) setManualIncluded(false); }} /> Exclude from this plan</label>
          </fieldset>
          {(manualIncluded || manualExcluded) && (
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-override`}>Override Reason</label>
              <textarea id={`${titleId}-override`} className="field-control" rows={2} maxLength={1000} value={overrideReason} disabled={isSubmitting} onChange={(event) => setOverrideReason(event.target.value)} />
            </div>
          )}
          {error && <p className="schedule-baseline-error" role="alert">{error}</p>}
          <div className="dialog__actions">
            <Button disabled={isSubmitting} onClick={onCancel}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save Item"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}


export default LookAheadItemDialog;
