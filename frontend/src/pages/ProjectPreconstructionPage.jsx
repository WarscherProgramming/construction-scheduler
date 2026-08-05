import { useState } from "react";

import AddReviewSourceDialog from "../components/preconstruction/AddReviewSourceDialog";
import ReviewSetDialog from "../components/preconstruction/ReviewSetDialog";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import usePreconstruction from "../hooks/usePreconstruction";
import { formatDisplayDate } from "../utils/date";


function ignoreFailure(promise) {
  void promise.catch(() => {});
}


function ProjectPreconstructionPage({
  projectId,
  projectName = "Project",
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const preconstruction = usePreconstruction({ projectId, onError: onRequestError });
  const [reviewDialog, setReviewDialog] = useState(null);
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
  const [confirmation, setConfirmation] = useState(null);
  const { detail } = preconstruction;
  const reviewSet = detail.reviewSet;

  const confirm = async () => {
    const action = confirmation?.action;
    if (!action) return;
    try {
      await action();
      setConfirmation(null);
    } catch {
      // Global feedback already reports the request failure.
    }
  };

  const openSource = (source) => {
    const target = source.route_target;
    onNavigate(target.page, target.projectId, target);
  };

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectPreconstruction"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="project-preconstruction-page"
    >
      <PageHeader
        title="Preconstruction"
        eyebrow={projectName}
        actions={
          <Button variant="primary" onClick={() => setReviewDialog("create")}>
            <Icon name="plus" size={16} />
            Create Review Set
          </Button>
        }
      />

      <div className="preconstruction-workspace">
        <aside className="preconstruction-review-sets" aria-labelledby="review-set-list-title">
          <div className="preconstruction-section-heading">
            <div>
              <h2 id="review-set-list-title">Review Sets</h2>
              <p>{preconstruction.reviewSets.length} shown</p>
            </div>
            <label>
              <span className="sr-only">Review set status</span>
              <select value={preconstruction.filter} onChange={(event) => preconstruction.setFilter(event.target.value)}>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
                <option value="all">All</option>
              </select>
            </label>
          </div>
          {preconstruction.isListLoading ? (
            <LoadingState message="Loading review sets..." />
          ) : preconstruction.listError ? (
            <div className="preconstruction-local-error" role="alert">
              <p>Review sets could not be loaded.</p>
              <Button onClick={preconstruction.refreshList}>Retry</Button>
            </div>
          ) : preconstruction.reviewSets.length ? (
            <ul className="preconstruction-review-set-list">
              {preconstruction.reviewSets.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={item.id === preconstruction.selectedReviewSetId ? "is-selected" : ""}
                    aria-pressed={item.id === preconstruction.selectedReviewSetId}
                    onClick={() => preconstruction.selectReviewSet(item.id)}
                  >
                    <span><strong>{item.name}</strong><small>{item.purpose_label}</small></span>
                    <StatusBadge value={item.status} />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No review sets" announce={false} />
          )}
        </aside>

        <section className="preconstruction-detail" aria-label="Selected review set">
          {!preconstruction.selectedReviewSetId ? (
            <EmptyState title="Select a review set" announce={false} />
          ) : preconstruction.isDetailLoading ? (
            <LoadingState message="Loading review details..." />
          ) : preconstruction.detailError ? (
            <div className="preconstruction-local-error" role="alert">
              <h2>Review details unavailable</h2>
              <Button onClick={preconstruction.refreshDetail}>Retry</Button>
            </div>
          ) : reviewSet ? (
            <>
              <header className="preconstruction-detail-header">
                <div>
                  <p>{reviewSet.purpose_label}</p>
                  <h2>{reviewSet.name}</h2>
                  {reviewSet.description && <p>{reviewSet.description}</p>}
                </div>
                <div className="preconstruction-actions">
                  <StatusBadge value={reviewSet.status} />
                  {reviewSet.status === "draft" && (
                    <Button size="sm" onClick={() => setReviewDialog("edit")}>Edit</Button>
                  )}
                  {reviewSet.status !== "archived" && (
                    <Button
                      size="sm"
                      onClick={() => setConfirmation({
                        title: "Archive Review Set",
                        message: `Archive ${reviewSet.name}? Its history remains viewable.`,
                        label: "Archive Review Set",
                        action: preconstruction.archiveReviewSet,
                      })}
                    >Archive</Button>
                  )}
                </div>
              </header>

              <section className="preconstruction-panel" aria-labelledby="review-sources-title">
                <div className="preconstruction-section-heading">
                  <div><h3 id="review-sources-title">Review Sources</h3><p>{detail.sources.length} active sources</p></div>
                  {reviewSet.status === "draft" && (
                    <Button size="sm" onClick={() => setSourceDialogOpen(true)}>
                      <Icon name="plus" size={15} /> Add Source
                    </Button>
                  )}
                </div>
                {detail.sources.length ? (
                  <ul className="preconstruction-source-list">
                    {detail.sources.map((source) => (
                      <li key={source.id}>
                        <div className="preconstruction-source-main">
                          <button type="button" onClick={() => openSource(source)}>{source.display_name}</button>
                          <span>{source.role_label} · {source.role_category}</span>
                        </div>
                        <StatusBadge value={source.extraction_status} />
                        {reviewSet.status === "draft" && !source.locked && (
                          <>
                            <label>
                              <span className="sr-only">Role for {source.display_name}</span>
                              <select
                                value={source.document_role}
                                disabled={preconstruction.isSaving}
                                onChange={(event) => ignoreFailure(
                                  preconstruction.updateSource(source.id, {
                                    document_role: event.target.value,
                                  })
                                )}
                              >
                                {detail.roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
                              </select>
                            </label>
                            <Button
                              size="sm"
                              variant="ghost"
                              aria-label={`Remove ${source.display_name}`}
                              onClick={() => setConfirmation({
                                title: "Remove Review Source",
                                message: `Remove ${source.display_name} from this review set?`,
                                label: "Remove Source",
                                destructive: true,
                                action: () => preconstruction.removeSource(source.id),
                              })}
                            ><Icon name="trash" size={16} /></Button>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : <EmptyState title="No review sources" announce={false} />}
              </section>

              <section className="preconstruction-panel" aria-labelledby="readiness-title">
                <div className="preconstruction-section-heading">
                  <div><h3 id="readiness-title">Readiness</h3><p>Deterministic source and provider checks</p></div>
                  <Button size="sm" onClick={preconstruction.refreshDetail}><Icon name="refresh" size={15} />Refresh</Button>
                </div>
                {detail.readiness && (
                  <div className="preconstruction-readiness">
                    <p className="preconstruction-readiness__status">
                      <StatusBadge value={detail.readiness.ready ? "Ready" : "Not Ready"} />
                      <span>{detail.readiness.provider.available ? `Provider ${detail.readiness.provider.profile} available` : "AI provider is disabled"}</span>
                    </p>
                    <dl>
                      <div><dt>Requirement</dt><dd>{detail.readiness.requirement_source_count}</dd></div>
                      <div><dt>Coverage</dt><dd>{detail.readiness.coverage_source_count}</dd></div>
                      <div><dt>Context</dt><dd>{detail.readiness.context_source_count}</dd></div>
                      <div><dt>Searchable</dt><dd>{detail.readiness.searchable_source_count}</dd></div>
                    </dl>
                    {detail.readiness.blockers.length > 0 && <div><h4>Blockers</h4><ul>{detail.readiness.blockers.map((item) => <li key={item}>{item}</li>)}</ul></div>}
                    {detail.readiness.warnings.length > 0 && <div><h4>Warnings</h4><ul>{detail.readiness.warnings.map((item) => <li key={item}>{item}</li>)}</ul></div>}
                  </div>
                )}
              </section>

              <section className="preconstruction-panel" aria-labelledby="analysis-runs-title">
                <div className="preconstruction-section-heading">
                  <div><h3 id="analysis-runs-title">Analysis Runs</h3><p>Provider contract validation only</p></div>
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={!detail.readiness?.ready || preconstruction.isSaving || reviewSet.status === "archived"}
                    title={detail.readiness?.ready ? "Request analysis run" : "Resolve readiness blockers before requesting a run"}
                    onClick={() => ignoreFailure(preconstruction.requestRun())}
                  >Request Run</Button>
                </div>
                {detail.runs.length ? (
                  <ul className="preconstruction-run-list">
                    {detail.runs.map((run) => (
                      <li key={run.id}>
                        <div><strong>Run {run.id}</strong><span>{run.analysis_type_label} · {formatDisplayDate(run.requested_at)}</span></div>
                        <StatusBadge value={run.status} />
                        <span>Attempt {run.attempt_count} of {run.max_attempts}</span>
                        {run.failure_message && <p>{run.failure_message}</p>}
                        <div className="preconstruction-actions">
                          {run.can_cancel && <Button size="sm" onClick={() => ignoreFailure(preconstruction.cancelRun(run.id))}>Cancel Run {run.id}</Button>}
                          {run.can_retry && <Button size="sm" onClick={() => ignoreFailure(preconstruction.retryRun(run.id))}>Retry Run {run.id}</Button>}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <EmptyState title="No analysis runs" announce={false} />}
              </section>
            </>
          ) : null}
        </section>
      </div>

      {reviewDialog && (
        <ReviewSetDialog
          reviewSet={reviewDialog === "edit" ? reviewSet : null}
          busy={preconstruction.isSaving}
          onClose={() => setReviewDialog(null)}
          onSubmit={reviewDialog === "edit" ? preconstruction.updateReviewSet : preconstruction.createReviewSet}
        />
      )}
      {sourceDialogOpen && (
        <AddReviewSourceDialog
          roles={detail.roles}
          existingSources={detail.sources}
          candidates={preconstruction.candidates}
          isSearching={preconstruction.isCandidateLoading}
          busy={preconstruction.isSaving}
          onSearch={preconstruction.searchCandidates}
          onAdd={preconstruction.addSource}
          onClose={() => setSourceDialogOpen(false)}
        />
      )}
      <ConfirmDialog
        open={Boolean(confirmation)}
        title={confirmation?.title || "Confirm"}
        message={confirmation?.message || ""}
        confirmLabel={confirmation?.label}
        destructive={confirmation?.destructive}
        confirmDisabled={preconstruction.isSaving}
        onConfirm={confirm}
        onCancel={() => setConfirmation(null)}
      />
    </ProjectLayout>
  );
}

export default ProjectPreconstructionPage;
