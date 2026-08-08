import { useState } from "react";

import Button from "../ui/Button";
import Card from "../ui/Card";


function ComparisonPlanList({ plans, selectedPlanId, onSelect, onCreate, onArchive, busy }) {
  return (
    <div className="comparison-plan-list">
      <div className="comparison-plan-controls">
        <label className="field-group">
          <span>Comparison plan</span>
          <select
            value={selectedPlanId || ""}
            onChange={(event) => onSelect(Number(event.target.value))}
            disabled={plans.length === 0}
          >
            {plans.length === 0 && <option value="">No comparison plans</option>}
            {plans.map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name} — {plan.comparison_type_label} ({plan.status})
              </option>
            ))}
          </select>
        </label>
        <div className="comparison-plan-actions">
          <Button variant="primary" onClick={onCreate} disabled={busy}>
            New plan
          </Button>
          {selectedPlanId && (
            <Button onClick={() => onArchive(selectedPlanId)} disabled={busy}>
              Archive plan
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}


function ComparisonReadinessPanel({ readiness, onRun, busy, archived }) {
  if (!readiness) return null;
  const metrics = [
    ["Requirement assertions", readiness.requirement_assertion_count],
    ["Coverage assertions", readiness.coverage_assertion_count],
    ["Accepted assertions", readiness.accepted_assertion_count],
    ["Stale assertions", readiness.stale_assertion_count],
    ["Unsupported taxonomy", readiness.unsupported_taxonomy_count],
  ];
  return (
    <section className="comparison-readiness" aria-label="Comparison readiness">
      <h4>Comparison readiness</h4>
      <dl className="comparison-readiness-metrics" role="group" aria-label="Comparison readiness metrics">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="preconstruction-hint">
        Deterministic comparison:{" "}
        {readiness.deterministic_comparison_available ? "Available" : "Unavailable"}
        {" · "}
        Provider validation:{" "}
        {readiness.provider_validation_available ? "Available" : "Unavailable"}
        {" · "}
        Taxonomy {readiness.taxonomy_version}
      </p>
      {readiness.blockers.length > 0 && (
        <ul className="comparison-blockers">
          {readiness.blockers.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {readiness.warnings.length > 0 && (
        <ul className="comparison-warnings">
          {readiness.warnings.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      <Button
        variant="primary"
        onClick={onRun}
        disabled={busy || !readiness.ready || archived}
      >
        {busy ? "Running comparison…" : "Run comparison"}
      </Button>
    </section>
  );
}


function ExecutionPanel({ diagnostics, execution }) {
  if (!diagnostics && !execution) return null;
  const budget = diagnostics?.pair_budget;
  const latest = execution?.items?.[0];
  const summary = execution?.summary;
  return (
    <section className="comparison-execution" aria-label="Execution diagnostics">
      <h4>Execution</h4>
      <dl
        className="comparison-execution-metrics"
        role="group"
        aria-label="Execution diagnostics metrics"
      >
        {budget && (
          <>
            <div>
              <dt>Comparisons to perform</dt>
              <dd>{budget.estimated_pairs}</dd>
            </div>
            <div>
              <dt>Pair budget</dt>
              <dd>
                {budget.maximum_pairs}
                {budget.within_budget ? " · Within budget" : " · Exceeded"}
              </dd>
            </div>
          </>
        )}
        {latest && (
          <>
            <div>
              <dt>Last run duration</dt>
              <dd>{latest.duration_ms} ms</dd>
            </div>
            <div>
              <dt>Last run reused</dt>
              <dd>{latest.manifest_reused ? "Yes" : "No"}</dd>
            </div>
          </>
        )}
        {summary && (
          <div>
            <dt>Recorded executions</dt>
            <dd>{summary.total_executions}</dd>
          </div>
        )}
        {summary && (
          <div>
            <dt>Estimated cost</dt>
            <dd>
              {summary.cost_rate_configured
                ? summary.estimated_cost_display
                : "No rate configured"}
            </dd>
          </div>
        )}
      </dl>
      {latest?.budget_stop_label && (
        <p className="preconstruction-hint">
          Last run stopped early: {latest.budget_stop_label}.
        </p>
      )}
    </section>
  );
}


function FindingSummary({ summary, sets, selectedSetId, taxonomyVersion, onSelectSet }) {
  if (!summary) return null;
  const metrics = [
    ["Total", summary.total],
    ["Missing coverage", summary.missing_coverage],
    ["Partial coverage", summary.partial_coverage],
    ["Conflicts", summary.conflicts],
    ["Exclusions", summary.exclusions],
    ["Revision impacts", summary.revision_impacts],
    ["Proposed", summary.proposed],
    ["Accepted", summary.accepted],
    ["Needs review", summary.needs_review],
    ["Intentional exclusions", summary.intentional_exclusion],
    ["Rejected", summary.rejected],
    ["Human authored", summary.manual],
  ];
  const selected = sets.find((item) => String(item.id) === String(selectedSetId));
  return (
    <div className="finding-summary">
      <dl className="finding-summary-metrics" role="group" aria-label="Finding review summary">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <label className="field-group">
        <span>Finding set</span>
        <select
          value={selectedSetId || ""}
          onChange={(event) => onSelectSet(event.target.value || undefined)}
        >
          <option value="">All sets (including human authored)</option>
          {sets.map((item) => (
            <option key={item.id} value={item.id}>
              Set {item.id} · {item.finding_count} findings ·{" "}
              {new Date(item.created_at).toLocaleString()}
            </option>
          ))}
        </select>
      </label>
      {selected && (
        <p className="preconstruction-hint">
          Provider profile {selected.provider_profile} · manifest{" "}
          {selected.comparison_manifest_hash.slice(0, 12)}… · content{" "}
          {selected.content_hash.slice(0, 12)}… · {selected.candidate_count} candidate(s) ·{" "}
          {selected.warning_count} warning(s)
        </p>
      )}
      {taxonomyVersion && (
        <p className="preconstruction-hint">Taxonomy version {taxonomyVersion}</p>
      )}
    </div>
  );
}


function FindingFilters({ query, onChange }) {
  return (
    <div className="finding-filters" role="group" aria-label="Finding filters">
      <label className="field-group">
        <span>Review status</span>
        <select
          value={query.reviewStatus || ""}
          onChange={(event) =>
            onChange({ reviewStatus: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All statuses</option>
          <option value="proposed">Proposed</option>
          <option value="needs_review">Needs review</option>
          <option value="accepted">Accepted</option>
          <option value="intentional_exclusion">Intentional exclusion</option>
          <option value="rejected">Rejected</option>
          <option value="superseded">Superseded</option>
        </select>
      </label>
      <label className="field-group">
        <span>Finding type</span>
        <select
          value={query.findingType || ""}
          onChange={(event) =>
            onChange({ findingType: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All types</option>
          <option value="missing_coverage">Missing coverage</option>
          <option value="partial_coverage">Partial coverage</option>
          <option value="conflicting_scope">Conflicting scope</option>
          <option value="explicit_exclusion">Explicit exclusion</option>
          <option value="conditional_scope">Conditional scope</option>
          <option value="responsibility_conflict">Responsibility conflict</option>
          <option value="quantity_mismatch">Quantity mismatch</option>
          <option value="location_mismatch">Location mismatch</option>
          <option value="revision_added_scope">Revision added scope</option>
          <option value="revision_removed_scope">Revision removed scope</option>
          <option value="revision_changed_scope">Revision changed scope</option>
        </select>
      </label>
      <label className="field-group">
        <span>Severity</span>
        <select
          value={query.severity || ""}
          onChange={(event) =>
            onChange({ severity: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="informational">Informational</option>
        </select>
      </label>
      <label className="field-group">
        <span>Origin</span>
        <select
          value={query.origin || ""}
          onChange={(event) =>
            onChange({ origin: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All origins</option>
          <option value="deterministic">Deterministic</option>
          <option value="provider_validated">Provider validated</option>
          <option value="manual">Human authored</option>
        </select>
      </label>
      <label className="field-group">
        <span>Search</span>
        <input
          value={query.search || ""}
          maxLength="200"
          onChange={(event) => onChange({ search: event.target.value, offset: 0 })}
        />
      </label>
    </div>
  );
}


function FindingDetailPanel({ finding, onInspect }) {
  const requirement = finding.assertions.filter(
    (item) => item.side === "requirement" || item.side === "prior_revision"
  );
  const coverage = finding.assertions.filter(
    (item) => item.side !== "requirement" && item.side !== "prior_revision"
  );
  return (
    <Card
      as="section"
      className="finding-detail"
      aria-label={`Finding detail: ${finding.title}`}
    >
      <h4>{finding.title}</h4>
      {finding.summary && <p className="finding-detail-summary">{finding.summary}</p>}
      {finding.rationale && (
        <p className="finding-detail-rationale">{finding.rationale}</p>
      )}
      <dl className="finding-detail-fields">
        <div>
          <dt>Finding type</dt>
          <dd>{finding.finding_type_label}</dd>
        </div>
        <div>
          <dt>Severity</dt>
          <dd>{finding.severity_label}</dd>
        </div>
        <div>
          <dt>Origin</dt>
          <dd>{finding.origin_label}</dd>
        </div>
        <div>
          <dt>Match class</dt>
          <dd>
            {finding.deterministic_match_class_label}
            {finding.deterministic_match_score !== null
              ? ` (score ${finding.deterministic_match_score})`
              : ""}
          </dd>
        </div>
        <div>
          <dt>Current decision</dt>
          <dd>{finding.status_label}</dd>
        </div>
        {finding.review_reason_label && (
          <div>
            <dt>Reason</dt>
            <dd>{finding.review_reason_label}</dd>
          </div>
        )}
        {finding.provider_confidence !== null && (
          <div>
            <dt>Provider confidence</dt>
            <dd>{Math.round(finding.provider_confidence * 100)}%</dd>
          </div>
        )}
      </dl>

      {finding.match_reasons.length > 0 && (
        <>
          <h5>Match reasons</h5>
          <ul className="finding-match-reasons">
            {finding.match_reasons.map((reason) => (
              <li key={reason.code}>{reason.label}</li>
            ))}
          </ul>
        </>
      )}

      {[["Requirement side", requirement], ["Coverage side", coverage]].map(
        ([label, group]) =>
          group.length > 0 && (
            <div key={label}>
              <h5>{label}</h5>
              <ul className="finding-assertion-list">
                {group.map((item) => (
                  <li key={`${item.assertion_id}-${item.side}`}>
                    <p className="finding-assertion-subject">{item.subject}</p>
                    <p className="finding-assertion-meta">
                      {item.concept_category_label} · {item.concept_name} ·{" "}
                      {item.side_label} · {item.link_role_label} · match{" "}
                      {item.match_class_label}
                    </p>
                    <p className="finding-assertion-meta">
                      {item.source_display_name || "Source unavailable"}
                      {item.document_role ? ` · ${item.document_role}` : ""}
                      {item.inclusion_state ? ` · ${item.inclusion_state}` : ""}
                      {item.responsibility_party
                        ? ` · responsibility ${item.responsibility_party}`
                        : ""}
                      {item.quantity_value !== null && item.quantity_value !== undefined
                        ? ` · ${item.quantity_value} ${item.quantity_unit || ""}`
                        : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )
      )}

      <h5>Evidence</h5>
      {finding.evidence.length === 0 ? (
        <p>No evidence is attached to this finding.</p>
      ) : (
        <ul className="finding-evidence-list">
          {finding.evidence.map((item) => (
            <li key={item.id}>
              <p className="finding-evidence-meta">
                {item.source_display_name || "Source unavailable"} · page{" "}
                {item.page_number} · segment {item.segment_index} · {item.evidence_role}
              </p>
              {/* Plain text only: never rendered as HTML or Markdown. */}
              <p className="finding-evidence-excerpt">{item.excerpt}</p>
              <Button
                onClick={() =>
                  onInspect(item.content_target.sourceId, {
                    snapshotId: item.content_target.snapshotId,
                    page: item.content_target.pageNumber,
                  })
                }
              >
                Open in Content Inspector
              </Button>
            </li>
          ))}
        </ul>
      )}
      {finding.evidence_truncated && (
        <p className="preconstruction-hint">
          Additional evidence is not shown in this view.
        </p>
      )}
    </Card>
  );
}


const EMPTY_FOLLOW_UPS = {
  findingId: null,
  items: [],
  actions: [],
  availableActions: [],
  drafts: [],
  eligible: false,
  findingStatus: null,
};


function FollowUpItem({ item, busy, onLink, onClose }) {
  return (
    <li className="follow-up-item">
      <p className="follow-up-item-title">{item.draft_title}</p>
      <p className="follow-up-item-meta">
        {item.action_label} · Status: {item.status_label}
        {item.target
          ? ` · Linked to ${item.target.identifier}`
          : item.can_link
            ? " · Not linked yet"
            : ""}
      </p>
      {item.finding_no_longer_accepted && (
        <p className="follow-up-item-warning" role="status">
          The finding is now {item.finding_status_label}. This follow-up is kept
          as history and is not rewritten.
        </p>
      )}
      {/* Plain text only: never rendered as HTML or Markdown. */}
      <p className="follow-up-item-draft">{item.draft_body}</p>
      {item.closure_note && (
        <p className="follow-up-item-meta">Closing note: {item.closure_note}</p>
      )}
      <div className="follow-up-item-actions">
        {item.can_link && (
          <Button
            onClick={() => onLink(item)}
            disabled={busy}
          >
            Link existing record to {item.action_label}
          </Button>
        )}
        {item.can_close && (
          <Button onClick={() => onClose(item)} disabled={busy}>
            Close {item.action_label} follow-up
          </Button>
        )}
      </div>
    </li>
  );
}


function FollowUpPanel({
  finding,
  followUps,
  isLoading,
  busy,
  onRaise,
  onLink,
  onClose,
}) {
  const forThisFinding = followUps.findingId === finding.id;
  const items = forThisFinding ? followUps.items : [];
  const available = forThisFinding ? followUps.availableActions : [];
  const eligible = forThisFinding && followUps.eligible;

  return (
    <section className="follow-up-panel" aria-label={`Follow-up actions: ${finding.title}`}>
      <h5>Follow-up actions</h5>
      <p className="preconstruction-hint">
        A follow-up records that you decided to act on this accepted finding.
        FieldFlow creates no RFI, Change Order, or Submittal for you: create the
        record in its own workflow, then link it here.
      </p>

      {isLoading && <p role="status">Loading follow-up actions…</p>}

      {!isLoading && !eligible && items.length === 0 && (
        <p className="preconstruction-empty">
          Only an accepted finding can raise a follow-up. This finding is{" "}
          {finding.status_label}.
        </p>
      )}

      {items.length > 0 && (
        <ul className="follow-up-list" aria-label="Raised follow-up actions">
          {items.map((item) => (
            <FollowUpItem
              key={item.id}
              item={item}
              busy={busy}
              onLink={onLink}
              onClose={onClose}
            />
          ))}
        </ul>
      )}

      {eligible && available.length > 0 && (
        <div className="follow-up-actions">
          {available.map((action) => (
            <Button
              key={action.value}
              onClick={() => onRaise(finding, action.value)}
              disabled={busy}
            >
              Raise {action.label}
            </Button>
          ))}
        </div>
      )}
    </section>
  );
}


function FindingListItem({ finding, selected, onSelect, onReview }) {
  const requirement = finding.assertions.find(
    (item) => item.side === "requirement" || item.side === "prior_revision"
  );
  const coverage = finding.assertions.find(
    (item) => item.side === "coverage" || item.side === "current_revision"
  );
  return (
    <li className={`finding-item${selected ? " is-selected" : ""}`}>
      <div className="finding-item-main">
        <p className="finding-item-type">
          {finding.finding_type_label} · Severity: {finding.severity_label}
        </p>
        <h4 className="finding-item-title">{finding.title}</h4>
        {finding.summary && (
          <p className="finding-item-summary">
            {finding.summary.slice(0, 240)}
            {finding.summary.length > 240 ? "…" : ""}
          </p>
        )}
        <p className="finding-item-meta">
          Requirement: {requirement?.source_display_name || "—"}
          {" · "}
          Coverage: {coverage?.source_display_name || "—"}
          {requirement?.concept_name ? ` · ${requirement.concept_name}` : ""}
        </p>
        <p className="finding-item-meta">
          Status: {finding.status_label} · Origin: {finding.origin_label} · Match:{" "}
          {finding.deterministic_match_class_label} · Evidence:{" "}
          {finding.evidence_count}
        </p>
      </div>
      <div className="finding-item-actions">
        <Button onClick={() => onSelect(finding)}>
          {selected ? "Hide detail" : "View detail"}
        </Button>
        <Button variant="primary" onClick={() => onReview(finding)}>
          Review
        </Button>
      </div>
    </li>
  );
}


function ScopeComparisonWorkspace({
  comparison,
  query,
  isLoading,
  error,
  isSaving,
  onChangeQuery,
  onRetry,
  onSelectPlan,
  onCreatePlan,
  onArchivePlan,
  onRunComparison,
  onReview,
  onCreateManual,
  onInspect,
  followUps = EMPTY_FOLLOW_UPS,
  isFollowUpLoading = false,
  onLoadFollowUps,
  onCloseFollowUps,
  onRaiseFollowUp,
  onLinkFollowUp,
  onCloseFollowUp,
}) {
  const [expandedId, setExpandedId] = useState(null);
  const { plans, selectedPlanId, readiness, findings, execution } = comparison;
  const { items, total, limit, offset, summary, sets } = findings;
  const selectedPlan = plans.find((item) => item.id === selectedPlanId);
  const archived = selectedPlan?.status === "archived";

  return (
    <Card as="section" className="comparison-workspace" aria-label="Scope comparison">
      <header className="comparison-workspace-header">
        <h3>Scope comparison</h3>
        <div className="comparison-workspace-actions">
          <Button onClick={onRetry} disabled={isLoading}>
            {isLoading ? "Refreshing comparison…" : "Refresh comparison"}
          </Button>
          {selectedPlanId && (
            <Button
              variant="primary"
              onClick={() => onCreateManual(selectedPlanId)}
              disabled={isSaving || archived}
            >
              Add finding
            </Button>
          )}
        </div>
      </header>

      <p className="preconstruction-hint">
        Findings are advisory statements about potential scope gaps and
        conflicts. They require human review and are not confirmed omissions,
        contract obligations, approved change orders, or legal conclusions.
      </p>

      {error ? (
        <div role="alert" className="preconstruction-error">
          <p>Unable to load scope comparison.</p>
          <Button onClick={onRetry}>Try again</Button>
        </div>
      ) : (
        <>
          <ComparisonPlanList
            plans={plans}
            selectedPlanId={selectedPlanId}
            onSelect={onSelectPlan}
            onCreate={onCreatePlan}
            onArchive={onArchivePlan}
            busy={isSaving}
          />

          {plans.length === 0 ? (
            <p className="preconstruction-empty">
              No comparison plans yet. Create a plan to compare accepted
              requirement scope against accepted coverage scope.
            </p>
          ) : (
            <>
              <ComparisonReadinessPanel
                readiness={readiness}
                busy={isSaving || isLoading}
                archived={archived}
                onRun={() => onRunComparison(selectedPlanId)}
              />

              <ExecutionPanel
                diagnostics={readiness?.diagnostics}
                execution={execution}
              />

              <FindingSummary
                summary={summary}
                sets={sets}
                selectedSetId={query.findingSetId}
                taxonomyVersion={findings.taxonomyVersion}
                onSelectSet={(value) =>
                  onChangeQuery({ findingSetId: value, offset: 0 })
                }
              />
              <FindingFilters query={query} onChange={onChangeQuery} />

              {isLoading && <p role="status">Loading scope findings…</p>}

              {!isLoading && items.length === 0 ? (
                <p className="preconstruction-empty">
                  No findings match the current filters. Run the comparison, or
                  add a human-authored finding.
                </p>
              ) : (
                <ul className="finding-list" aria-label="Scope findings">
                  {items.map((finding) => (
                    <div key={finding.id}>
                      <FindingListItem
                        finding={finding}
                        selected={expandedId === finding.id}
                        onSelect={(item) => {
                          const next = expandedId === item.id ? null : item.id;
                          setExpandedId(next);
                          if (next) onLoadFollowUps?.(item.id);
                          else onCloseFollowUps?.();
                        }}
                        onReview={onReview}
                      />
                      {expandedId === finding.id && (
                        <>
                          <FindingDetailPanel
                            finding={finding}
                            onInspect={onInspect}
                          />
                          <FollowUpPanel
                            finding={finding}
                            followUps={followUps}
                            isLoading={isFollowUpLoading}
                            busy={isSaving}
                            onRaise={onRaiseFollowUp}
                            onLink={onLinkFollowUp}
                            onClose={onCloseFollowUp}
                          />
                        </>
                      )}
                    </div>
                  ))}
                </ul>
              )}

              <div className="finding-pagination">
                <p>
                  Showing {items.length === 0 ? 0 : offset + 1}–
                  {offset + items.length} of {total}
                </p>
                <div>
                  <Button
                    disabled={offset === 0 || isLoading}
                    onClick={() =>
                      onChangeQuery({ offset: Math.max(0, offset - limit) })
                    }
                  >
                    Previous
                  </Button>
                  <Button
                    disabled={offset + limit >= total || isLoading}
                    onClick={() => onChangeQuery({ offset: offset + limit })}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </Card>
  );
}

export default ScopeComparisonWorkspace;
