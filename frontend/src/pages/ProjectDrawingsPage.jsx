import { useState } from "react";

import DrawingIssueSection from "../components/drawings/DrawingIssueSection";
import RevisionHistoryDialog from "../components/drawings/RevisionHistoryDialog";
import {
  DrawingIssueDialog,
  DrawingRevisionDialog,
  DrawingSetDialog,
  DrawingSheetDialog,
} from "../components/drawings/DrawingWorkflowDialogs";
import EmptyState from "../components/EmptyState";
import RelationshipPanel from "../components/relationships/RelationshipPanel";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import { SkeletonPanel } from "../components/ui/Skeleton";
import useDrawings from "../hooks/useDrawings";
import { formatDisplayDate } from "../utils/date";
import {
  DRAWING_DISCIPLINES,
  drawingDisciplineLabel,
} from "../utils/drawing";


function drawingErrorMessage(error) {
  if (error?.status === 403) {
    return "You do not have access to this project's drawings.";
  }
  if (error?.status === 404) {
    return "The requested drawing record is no longer available.";
  }
  if (error?.status === 429) {
    return "Drawing requests are temporarily limited. Try again shortly.";
  }
  return error?.message || "The drawing workflow could not be completed.";
}


function ProjectDrawingsPage({
  projectId,
  projectName = "Project",
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const drawings = useDrawings({ projectId, onError: onRequestError });
  const [searchDraft, setSearchDraft] = useState("");
  const [dialog, setDialog] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [relationshipSheetId, setRelationshipSheetId] = useState(null);
  const currentSet =
    drawings.drawingSets.find(
      (drawingSet) => drawingSet.id === drawings.selectedSetId
    ) || null;
  const register = drawings.register;
  const relationshipSheet = register?.sheets.find(
    (sheet) => sheet.id === relationshipSheetId
  );

  const isActive = (key) => drawings.activeOperations.includes(key);

  const openHistory = (sheet) => {
    setDialog({ type: "history", sheet });
    void drawings.loadRevisions(sheet.id);
  };

  const viewRevision = (sheet, revision) => {
    setDialog(null);
    onNavigate("drawingViewer", projectId, {
      sheetId: sheet.id,
      revisionId: revision.id,
    });
  };

  const handleConfirmation = async () => {
    if (!confirmation) return;
    let result = null;
    if (confirmation.type === "archive-set") {
      result = await drawings.archiveSet(confirmation.record.id);
    } else if (confirmation.type === "archive-sheet") {
      result = await drawings.archiveSheet(confirmation.record.id);
    } else if (confirmation.type === "issue") {
      result = await drawings.issueIssue(confirmation.record.id);
    } else if (confirmation.type === "void") {
      result = await drawings.voidIssue(confirmation.record.id);
    }
    if (result) setConfirmation(null);
  };

  const confirmationCopy = (() => {
    if (!confirmation) return {};
    const record = confirmation.record;
    if (confirmation.type === "archive-set") {
      return {
        title: `Archive ${record.name}?`,
        message:
          "The set will leave the active register. Its sheets, revisions, and issued history will be retained.",
        label: "Archive Drawing Set",
      };
    }
    if (confirmation.type === "archive-sheet") {
      return {
        title: `Archive ${record.sheet_number}?`,
        message:
          "The sheet will leave the active register. Every revision and issue reference will be retained.",
        label: "Archive Drawing Sheet",
      };
    }
    if (confirmation.type === "issue") {
      return {
        title: `Issue ${record.issue_number}?`,
        message:
          `${record.name}, dated ${formatDisplayDate(record.issue_date)}, includes ${record.revisions.length} sheet revisions. Issuing freezes membership; the issue can later be voided but not rewritten.`,
        label: "Issue Drawings",
      };
    }
    return {
      title: `Void ${record.issue_number}?`,
      message:
        "The issued record and its frozen membership will remain available as void history.",
      label: "Void Drawing Issue",
    };
  })();

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectDrawings"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="drawing-register-page"
    >
      <PageHeader
        title="Drawing Register"
        subtitle="Control construction sheets, revisions, and formal issues."
        actions={
          <>
            <Button onClick={() => setDialog({ type: "set" })}>
              <Icon name="plus" size={16} />
              New Set
            </Button>
            <Button
              variant="primary"
              disabled={!currentSet}
              onClick={() => setDialog({ type: "sheet" })}
            >
              <Icon name="upload" size={16} />
              Add Sheet
            </Button>
          </>
        }
      />

      {drawings.operationError && (
        <div className="document-explorer-alert" role="alert">
          <span>{drawingErrorMessage(drawings.operationError)}</span>
          <Button
            size="sm"
            variant="ghost"
            aria-label="Dismiss drawing error"
            onClick={drawings.clearOperationError}
          >
            <Icon name="x" size={16} />
          </Button>
        </div>
      )}

      <section
        className="drawing-sets-section"
        aria-labelledby="drawing-sets-title"
      >
        <div className="drawing-section-heading">
          <div>
            <p>Managed packages</p>
            <h2 id="drawing-sets-title">Drawing Sets</h2>
          </div>
        </div>
        {drawings.isLoadingSets ? (
          <SkeletonPanel label="Loading drawing sets..." lines={2} />
        ) : drawings.drawingSets.length === 0 ? (
          <EmptyState
            title="No drawing sets"
            description="Create a drawing set before registering sheets."
          />
        ) : (
          <div className="drawing-set-list">
            {drawings.drawingSets.map((drawingSet) => (
              <article
                key={drawingSet.id}
                className={
                  drawingSet.id === drawings.selectedSetId
                    ? "drawing-set-record drawing-set-record--selected"
                    : "drawing-set-record"
                }
              >
                <button
                  type="button"
                  className="drawing-set-record__select"
                  aria-current={
                    drawingSet.id === drawings.selectedSetId
                      ? "true"
                      : undefined
                  }
                  onClick={() => drawings.setSelectedSetId(drawingSet.id)}
                >
                  <span>
                    <strong>{drawingSet.name}</strong>
                    <small>
                      {drawingSet.sheet_count} sheets ·{" "}
                      {drawingSet.issue_count} issues
                    </small>
                  </span>
                  <StatusBadge value={drawingSet.status} />
                </button>
                <div className="drawing-set-record__actions">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setDialog({ type: "set", record: drawingSet })
                    }
                  >
                    <Icon name="pencil" size={14} />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setConfirmation({
                        type: "archive-set",
                        record: drawingSet,
                      })
                    }
                  >
                    Archive
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section
        className="drawing-register-section"
        aria-labelledby="drawing-register-title"
      >
        <div className="drawing-section-heading">
          <div>
            <p>Current sheet index</p>
            <h2 id="drawing-register-title">Project Drawing Register</h2>
          </div>
          <Button
            size="sm"
            disabled={drawings.isLoadingRegister}
            onClick={drawings.refresh}
          >
            <Icon name="refresh" size={15} />
            Refresh
          </Button>
        </div>
        <div className="drawing-register-filters">
          <form
            role="search"
            className="drawing-register-search"
            onSubmit={(event) => {
              event.preventDefault();
              drawings.updateQuery({ search: searchDraft.trim() });
            }}
          >
            <label htmlFor="drawing-search">Search drawings</label>
            <div>
              <input
                id="drawing-search"
                className="field-control"
                type="search"
                maxLength={200}
                placeholder="Sheet, title, revision, or set"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
              />
              <Button type="submit" aria-label="Search drawing register">
                <Icon name="search" size={16} />
              </Button>
            </div>
          </form>
          <label>
            <span>Drawing set</span>
            <select
              className="field-control"
              value={drawings.query.drawingSetId}
              onChange={(event) =>
                drawings.updateQuery({ drawingSetId: event.target.value })
              }
            >
              <option value="">All sets</option>
              {drawings.drawingSets.map((drawingSet) => (
                <option key={drawingSet.id} value={drawingSet.id}>
                  {drawingSet.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Discipline</span>
            <select
              className="field-control"
              value={drawings.query.discipline}
              onChange={(event) =>
                drawings.updateQuery({ discipline: event.target.value })
              }
            >
              <option value="">All disciplines</option>
              {DRAWING_DISCIPLINES.map(([code, label]) => (
                <option key={code} value={code}>{code} - {label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select
              className="field-control"
              value={drawings.query.sheetStatus}
              onChange={(event) =>
                drawings.updateQuery({ sheetStatus: event.target.value })
              }
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="void">Void</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label>
            <span>Sort</span>
            <select
              className="field-control"
              value={`${drawings.query.sort}:${drawings.query.order}`}
              onChange={(event) => {
                const [sort, order] = event.target.value.split(":");
                drawings.updateQuery({ sort, order });
              }}
            >
              <option value="sheet_number:asc">Sheet number</option>
              <option value="title:asc">Title</option>
              <option value="discipline:asc">Discipline</option>
              <option value="revision_date:desc">Revision date</option>
              <option value="updated_at:desc">Recently updated</option>
            </select>
          </label>
        </div>

        {drawings.isLoadingRegister ? (
          <SkeletonPanel label="Loading drawing register..." lines={5} />
        ) : !register ? (
          <div className="drawing-load-error" role="alert">
            <p>The drawing register could not be loaded.</p>
            <Button onClick={drawings.refresh}>Retry</Button>
          </div>
        ) : register.sheets.length === 0 ? (
          <EmptyState
            title={
              drawings.query.search
                ? "No drawings match this search"
                : "No registered drawing sheets"
            }
            description={
              currentSet
                ? `Add the first PDF sheet to ${currentSet.name}.`
                : "Create a drawing set to begin."
            }
          />
        ) : (
          <>
            <div className="drawing-register-table-wrap">
              <table className="drawing-register-table">
                <caption className="visually-hidden">
                  Project drawing sheets and current revisions
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sheet</th>
                    <th scope="col">Title</th>
                    <th scope="col">Discipline</th>
                    <th scope="col">Drawing set</th>
                    <th scope="col">Current revision</th>
                    <th scope="col">Status</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {register.sheets.map((sheet) => (
                    <tr key={sheet.id}>
                      <th scope="row" data-label="Sheet">
                        {sheet.sheet_number}
                      </th>
                      <td data-label="Title">{sheet.title}</td>
                      <td data-label="Discipline">
                        {drawingDisciplineLabel(sheet.discipline)}
                      </td>
                      <td data-label="Drawing set">
                        {sheet.drawing_set_name}
                      </td>
                      <td data-label="Current revision">
                        <span className="drawing-current-revision">
                          <strong>
                            Rev {sheet.current_revision?.revision_code}
                          </strong>
                          <span>Current Revision</span>
                          <time dateTime={sheet.current_revision?.revision_date}>
                            {formatDisplayDate(
                              sheet.current_revision?.revision_date
                            )}
                          </time>
                        </span>
                      </td>
                      <td data-label="Status">
                        <StatusBadge value={sheet.status} />
                      </td>
                      <td data-label="Actions">
                        <div className="drawing-row-actions">
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() =>
                              viewRevision(sheet, sheet.current_revision)
                            }
                            aria-label={`View current revision for ${sheet.sheet_number}`}
                          >
                            View
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => openHistory(sheet)}
                            aria-label={`Revision history for ${sheet.sheet_number}`}
                          >
                            History ({sheet.revision_count})
                          </Button>
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() =>
                              setDialog({ type: "revision", sheet })
                            }
                            aria-label={`Upload revision for ${sheet.sheet_number}`}
                          >
                            <Icon name="upload" size={14} />
                            Revision
                          </Button>
                          <Button
                            size="sm"
                            aria-expanded={relationshipSheet?.id === sheet.id}
                            aria-controls={`drawing-sheet-relationships-${sheet.id}`}
                            aria-label={`${
                              relationshipSheet?.id === sheet.id
                                ? "Close relationships"
                                : "Relationships"
                            } for ${sheet.sheet_number}`}
                            onClick={() =>
                              setRelationshipSheetId(
                                relationshipSheet?.id === sheet.id
                                  ? null
                                  : sheet.id
                              )
                            }
                          >
                            <Icon name="link" size={14} />
                            {relationshipSheet?.id === sheet.id
                              ? "Close"
                              : "Relationships"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              setConfirmation({
                                type: "archive-sheet",
                                record: sheet,
                              })
                            }
                            aria-label={`Archive ${sheet.sheet_number}`}
                          >
                            Archive
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="document-pagination" aria-label="Drawing register pages">
              <Button
                size="sm"
                disabled={register.pagination.offset === 0}
                onClick={() =>
                  drawings.updateQuery({
                    offset: Math.max(
                      0,
                      register.pagination.offset -
                        register.pagination.limit
                    ),
                  })
                }
              >
                Previous
              </Button>
              <span>
                {register.pagination.offset + 1}-
                {Math.min(
                  register.pagination.offset + register.sheets.length,
                  register.pagination.total
                )}{" "}
                of {register.pagination.total} sheets
              </span>
              <Button
                size="sm"
                disabled={!register.pagination.has_more}
                onClick={() =>
                  drawings.updateQuery({
                    offset:
                      register.pagination.offset +
                      register.pagination.limit,
                  })
                }
              >
                Next
              </Button>
            </div>
          </>
        )}
      </section>

      {relationshipSheet && (
        <div
          id={`drawing-sheet-relationships-${relationshipSheet.id}`}
          className="record-relationship-detail"
          role="region"
          aria-label={`Relationships for drawing sheet ${relationshipSheet.sheet_number}`}
        >
          <RelationshipPanel
            projectId={projectId}
            entityType="drawing_sheet"
            entityId={relationshipSheet.id}
            title={`${relationshipSheet.sheet_number} Relationships`}
            onNavigate={onNavigate}
            onError={onRequestError}
          />
        </div>
      )}

      {currentSet && (
        <DrawingIssueSection
          drawingSet={currentSet}
          sheets={drawings.setSheets}
          issues={drawings.issues}
          isLoading={drawings.isLoadingSetDetails}
          activeOperations={drawings.activeOperations}
          onCreate={() => setDialog({ type: "issue" })}
          onEdit={(issue) =>
            setDialog({ type: "issue", record: issue })
          }
          onAddRevision={drawings.addIssueRevision}
          onRemoveRevision={drawings.removeIssueRevision}
          onIssue={(issue) =>
            setConfirmation({ type: "issue", record: issue })
          }
          onVoid={(issue) =>
            setConfirmation({ type: "void", record: issue })
          }
        />
      )}

      {dialog?.type === "set" && (
        <DrawingSetDialog
          drawingSet={dialog.record}
          busy={isActive(
            dialog.record
              ? `update-set:${dialog.record.id}`
              : "create-set"
          )}
          onSubmit={(payload) =>
            dialog.record
              ? drawings.updateSet(dialog.record.id, payload)
              : drawings.createSet(payload)
          }
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.type === "sheet" && currentSet && (
        <DrawingSheetDialog
          drawingSet={currentSet}
          busy={isActive("create-sheet")}
          onSubmit={drawings.createSheet}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.type === "revision" && (
        <DrawingRevisionDialog
          sheet={dialog.sheet}
          busy={isActive(`upload-revision:${dialog.sheet.id}`)}
          onSubmit={drawings.uploadRevision}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.type === "history" && (
        <RevisionHistoryDialog
          sheet={dialog.sheet}
          revisions={
            drawings.revisionSheetId === dialog.sheet.id
              ? drawings.revisions
              : []
          }
          isLoading={drawings.isLoadingRevisions}
          activeOperations={drawings.activeOperations}
          onView={(revision) => viewRevision(dialog.sheet, revision)}
          onDownload={drawings.downloadRevision}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.type === "issue" && currentSet && (
        <DrawingIssueDialog
          drawingSet={currentSet}
          issue={dialog.record}
          busy={isActive(
            dialog.record
              ? `update-issue:${dialog.record.id}`
              : "create-issue"
          )}
          onSubmit={(payload) =>
            dialog.record
              ? drawings.updateIssue(dialog.record.id, payload)
              : drawings.createIssue(currentSet.id, payload)
          }
          onClose={() => setDialog(null)}
        />
      )}

      <ConfirmDialog
        open={Boolean(confirmation)}
        destructive={
          confirmation?.type === "archive-set" ||
          confirmation?.type === "archive-sheet" ||
          confirmation?.type === "void"
        }
        title={confirmationCopy.title}
        message={confirmationCopy.message}
        confirmLabel={confirmationCopy.label}
        confirmDisabled={
          Boolean(confirmation) &&
          (
            confirmation.type === "archive-set"
              ? isActive(`archive-set:${confirmation.record.id}`)
              : confirmation.type === "archive-sheet"
                ? isActive(`archive-sheet:${confirmation.record.id}`)
                : confirmation.type === "issue"
                  ? isActive(`issue:${confirmation.record.id}`)
                  : isActive(`void:${confirmation.record.id}`)
          )
        }
        onConfirm={handleConfirmation}
        onCancel={() => setConfirmation(null)}
      />
    </ProjectLayout>
  );
}

export default ProjectDrawingsPage;
