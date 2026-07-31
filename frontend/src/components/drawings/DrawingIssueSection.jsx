import { useState } from "react";

import { formatDisplayDate } from "../../utils/date";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import StatusBadge from "../StatusBadge";


function DrawingIssueSection({
  drawingSet,
  sheets,
  issues,
  isLoading,
  activeOperations,
  onCreate,
  onEdit,
  onAddRevision,
  onRemoveRevision,
  onIssue,
  onVoid,
}) {
  const [selections, setSelections] = useState({});

  return (
    <section
      className="drawing-issues-section"
      aria-labelledby="drawing-issues-title"
    >
      <div className="drawing-section-heading">
        <div>
          <p>Formal issuance</p>
          <h2 id="drawing-issues-title">Drawing Issues</h2>
        </div>
        <Button variant="primary" onClick={onCreate}>
          <Icon name="plus" size={16} />
          New Draft Issue
        </Button>
      </div>
      {isLoading ? (
        <p role="status">Loading drawing issues...</p>
      ) : issues.length === 0 ? (
        <p className="drawing-inline-empty">
          No drawing issues exist for {drawingSet.name}.
        </p>
      ) : (
        <div className="drawing-issue-list">
          {issues.map((issue) => {
            const included = new Set(
              issue.revisions.map((revision) => revision.revision_id)
            );
            const candidates = sheets
              .map((sheet) => sheet.current_revision)
              .filter(
                (revision) => revision && !included.has(revision.id)
              );
            const selected = selections[issue.id] || "";
            const isDraft = issue.status === "draft";
            return (
              <article key={issue.id} className="drawing-issue-record">
                <div className="drawing-issue-record__heading">
                  <div>
                    <h3>{issue.issue_number} - {issue.name}</h3>
                    <p>
                      {formatDisplayDate(issue.issue_date)} ·{" "}
                      {issue.purpose.replace("_", " ")}
                    </p>
                  </div>
                  <StatusBadge value={issue.status} />
                </div>
                {issue.notes && <p>{issue.notes}</p>}
                <div className="drawing-issue-members">
                  <h4>Included revisions ({issue.revisions.length})</h4>
                  {issue.revisions.length === 0 ? (
                    <p>No revisions have been added.</p>
                  ) : (
                    <ul>
                      {issue.revisions.map((revision) => (
                        <li key={revision.revision_id}>
                          <span>
                            <strong>{revision.sheet_number}</strong>{" "}
                            Rev {revision.revision_code}
                            {!revision.is_current && " · Superseded"}
                          </span>
                          {isDraft && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={activeOperations.includes(
                                `issue-remove:${issue.id}:${revision.revision_id}`
                              )}
                              onClick={() =>
                                onRemoveRevision(
                                  issue.id,
                                  revision.revision_id
                                )
                              }
                              aria-label={`Remove ${revision.sheet_number} revision ${revision.revision_code} from ${issue.name}`}
                            >
                              <Icon name="x" size={14} />
                              Remove
                            </Button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                {isDraft && (
                  <div className="drawing-issue-add">
                    <label htmlFor={`issue-revision-${issue.id}`}>
                      Add current revision
                    </label>
                    <select
                      id={`issue-revision-${issue.id}`}
                      className="field-control"
                      value={selected}
                      onChange={(event) =>
                        setSelections((current) => ({
                          ...current,
                          [issue.id]: event.target.value,
                        }))
                      }
                    >
                      <option value="">Select a sheet</option>
                      {candidates.map((revision) => {
                        const sheet = sheets.find(
                          (item) => item.id === revision.drawing_sheet_id
                        );
                        return (
                          <option key={revision.id} value={revision.id}>
                            {sheet?.sheet_number} - Rev {revision.revision_code}
                          </option>
                        );
                      })}
                    </select>
                    <Button
                      size="sm"
                      disabled={
                        !selected ||
                        activeOperations.includes(`issue-add:${issue.id}`)
                      }
                      onClick={async () => {
                        const result = await onAddRevision(
                          issue.id,
                          Number(selected)
                        );
                        if (result) {
                          setSelections((current) => ({
                            ...current,
                            [issue.id]: "",
                          }));
                        }
                      }}
                    >
                      <Icon name="plus" size={14} />
                      Add
                    </Button>
                  </div>
                )}
                <div className="drawing-issue-record__actions">
                  {isDraft && (
                    <>
                      <Button size="sm" onClick={() => onEdit(issue)}>
                        <Icon name="pencil" size={14} />
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={
                          issue.revisions.length === 0 ||
                          activeOperations.includes(`issue:${issue.id}`)
                        }
                        onClick={() => onIssue(issue)}
                      >
                        Issue Drawings
                      </Button>
                    </>
                  )}
                  {issue.status === "issued" && (
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={activeOperations.includes(`void:${issue.id}`)}
                      onClick={() => onVoid(issue)}
                    >
                      Void Issue
                    </Button>
                  )}
                  {issue.status !== "draft" && (
                    <span className="drawing-membership-frozen">
                      <Icon name="info" size={14} />
                      Membership frozen
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default DrawingIssueSection;
