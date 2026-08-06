import { useState } from "react";

import Button from "../ui/Button";
import Card from "../ui/Card";


function formatConfidence(value) {
  if (value === null || value === undefined) return "Not applicable";
  return `${Math.round(value * 100)}%`;
}


function AssertionSummary({ summary, sets, selectedSetId, taxonomyVersion, onSelectSet }) {
  if (!summary) return null;
  const metrics = [
    ["Total", summary.total],
    ["Proposed", summary.proposed],
    ["Accepted", summary.accepted],
    ["Needs review", summary.needs_review],
    ["Rejected", summary.rejected],
    ["Superseded", summary.superseded],
    ["Human authored", summary.manual],
  ];
  const selected = sets.find((item) => String(item.id) === String(selectedSetId));
  return (
    <div className="assertion-summary">
      <dl
        className="assertion-summary-metrics"
        role="group"
        aria-label="Assertion review summary"
      >
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="assertion-summary-meta">
        <label className="field-group">
          <span>Extraction set</span>
          <select
            value={selectedSetId || ""}
            onChange={(event) => onSelectSet(event.target.value || undefined)}
          >
            <option value="">All sets (including human authored)</option>
            {sets.map((item) => (
              <option key={item.id} value={item.id}>
                Set {item.id} · {item.assertion_count} assertions ·{" "}
                {new Date(item.created_at).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        {selected && (
          <p className="preconstruction-hint">
            Provider profile {selected.provider_profile} · taxonomy{" "}
            {selected.taxonomy_version} · manifest{" "}
            {selected.manifest_hash.slice(0, 12)}… · content{" "}
            {selected.content_hash.slice(0, 12)}… · {selected.warning_count} warning(s)
          </p>
        )}
        {taxonomyVersion && (
          <p className="preconstruction-hint">Taxonomy version {taxonomyVersion}</p>
        )}
      </div>
    </div>
  );
}


function AssertionFilters({ query, taxonomy, sources, onChange }) {
  return (
    <div className="assertion-filters" role="group" aria-label="Assertion filters">
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
          <option value="rejected">Rejected</option>
          <option value="superseded">Superseded</option>
        </select>
      </label>
      <label className="field-group">
        <span>Category</span>
        <select
          value={query.category || ""}
          onChange={(event) =>
            onChange({ category: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All categories</option>
          {(taxonomy?.categories || []).map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </label>
      <label className="field-group">
        <span>Assertion type</span>
        <select
          value={query.assertionType || ""}
          onChange={(event) =>
            onChange({ assertionType: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All types</option>
          {(taxonomy?.assertion_types || []).map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </label>
      <label className="field-group">
        <span>Source</span>
        <select
          value={query.sourceId || ""}
          onChange={(event) =>
            onChange({ sourceId: event.target.value || undefined, offset: 0 })
          }
        >
          <option value="">All sources</option>
          {sources.map((source) => (
            <option key={source.id} value={source.id}>{source.display_name}</option>
          ))}
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
          <option value="provider">Extracted</option>
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


function AssertionListItem({ assertion, selected, onSelect, onReview }) {
  return (
    <li className={`assertion-item${selected ? " is-selected" : ""}`}>
      <div className="assertion-item-main">
        <p className="assertion-item-concept">
          {assertion.concept_category_label} · {assertion.concept_name}
        </p>
        <h4 className="assertion-item-subject">{assertion.subject}</h4>
        {assertion.requirement_text && (
          <p className="assertion-item-requirement">
            {assertion.requirement_text.slice(0, 240)}
            {assertion.requirement_text.length > 240 ? "…" : ""}
          </p>
        )}
        <p className="assertion-item-meta">
          {assertion.assertion_type_label} · {assertion.inclusion_state_label} ·{" "}
          {assertion.source?.display_name || "Source unavailable"}
          {assertion.evidence[0]
            ? ` · page ${assertion.evidence[0].page_number}`
            : ""}
        </p>
        <p className="assertion-item-meta">
          Status: {assertion.status_label} · Origin: {assertion.origin_label} ·
          Confidence: {formatConfidence(assertion.confidence)} · Evidence:{" "}
          {assertion.evidence_count}
        </p>
      </div>
      <div className="assertion-item-actions">
        <Button onClick={() => onSelect(assertion)}>
          {selected ? "Hide detail" : "View detail"}
        </Button>
        <Button variant="primary" onClick={() => onReview(assertion)}>
          Review
        </Button>
      </div>
    </li>
  );
}


function AssertionDetailPanel({ assertion, onNavigate, onInspect }) {
  const fields = [
    ["Concept", `${assertion.concept_name} (${assertion.concept_code})`],
    ["Category", assertion.concept_category_label],
    ["Scope kind", assertion.concept_scope_kind],
    ["Assertion type", assertion.assertion_type_label],
    ["Inclusion", assertion.inclusion_state_label],
    ["Responsibility", assertion.responsibility_party],
    ["Discipline", assertion.discipline],
    ["Trade", assertion.trade],
    ["Specification section", assertion.specification_section],
    ["Drawing sheet", assertion.drawing_sheet],
    [
      "Quantity",
      assertion.quantity_value === null || assertion.quantity_value === undefined
        ? null
        : `${assertion.quantity_value}${assertion.quantity_unit ? ` ${assertion.quantity_unit}` : ""}`,
    ],
    ["Location", assertion.location_text],
    ["Confidence", formatConfidence(assertion.confidence)],
    ["Confidence basis", assertion.confidence_basis],
    ["Origin", assertion.origin_label],
    ["Taxonomy version", assertion.taxonomy_version],
    ["Current decision", assertion.status_label],
    ["Reason", assertion.review_reason_label],
    ["Reviewer note", assertion.reviewer_note],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");

  return (
    <Card
      as="section"
      className="assertion-detail"
      aria-label={`Assertion detail: ${assertion.subject}`}
    >
      <h4>{assertion.subject}</h4>
      {assertion.supersedes_assertion_id && (
        <p className="preconstruction-hint">
          Supersedes assertion {assertion.supersedes_assertion_id}
        </p>
      )}
      <dl className="assertion-detail-fields">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      <h5>Evidence</h5>
      {assertion.evidence.length === 0 ? (
        <p>No evidence is available for this assertion.</p>
      ) : (
        <ul className="assertion-evidence-list">
          {assertion.evidence.map((item) => (
            <li key={item.id}>
              <p className="assertion-evidence-meta">
                {item.source_display_name || "Source unavailable"} · page{" "}
                {item.page_number} · segment {item.segment_index} ·{" "}
                {item.evidence_role_label}
                {item.sheet_number ? ` · sheet ${item.sheet_number}` : ""}
              </p>
              {/* Plain text only: never rendered as HTML or Markdown. */}
              <p className="assertion-evidence-excerpt">{item.excerpt}</p>
              <div className="assertion-evidence-actions">
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
                {item.viewer_target?.page === "drawingViewer" && (
                  <Button
                    onClick={() =>
                      onNavigate("drawingViewer", item.viewer_target.projectId, {
                        sheetId: item.viewer_target.sheetId,
                        revisionId: item.viewer_target.revisionId,
                      })
                    }
                  >
                    Open drawing
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {assertion.evidence_truncated && (
        <p className="preconstruction-hint">
          Additional evidence is not shown in this view.
        </p>
      )}
    </Card>
  );
}


function ScopeAssertionWorkspace({
  assertions,
  query,
  taxonomy,
  sources,
  isLoading,
  error,
  isSaving,
  scopeAvailable,
  onChangeQuery,
  onRetry,
  onReview,
  onCreateManual,
  onSelectAssertion,
  selectedAssertionId,
  onNavigate,
  onInspect,
}) {
  const [expandedId, setExpandedId] = useState(selectedAssertionId || null);
  const { items, total, limit, offset, summary, sets } = assertions;

  const toggle = (assertion) => {
    const next = expandedId === assertion.id ? null : assertion.id;
    setExpandedId(next);
    onSelectAssertion?.(next);
  };

  return (
    <Card as="section" className="assertion-workspace" aria-label="Scope assertions">
      <header className="assertion-workspace-header">
        <h3>Scope assertions</h3>
        <div className="assertion-workspace-actions">
          <Button onClick={onRetry} disabled={isLoading}>
            {isLoading ? "Refreshing assertions…" : "Refresh assertions"}
          </Button>
          <Button variant="primary" onClick={onCreateManual} disabled={isSaving}>
            Add assertion
          </Button>
        </div>
      </header>

      <p className="preconstruction-hint">
        Assertions are advisory statements that require human review. They are
        not findings, contract obligations, or approved scope.
      </p>

      {!scopeAvailable && (
        <p className="preconstruction-hint">
          Scope extraction is unavailable in this environment because the AI
          provider is disabled. Human-authored assertions remain available.
        </p>
      )}

      {error ? (
        <div role="alert" className="preconstruction-error">
          <p>Unable to load scope assertions.</p>
          <Button onClick={onRetry}>Try again</Button>
        </div>
      ) : (
        <>
          <AssertionSummary
            summary={summary}
            sets={sets}
            selectedSetId={query.assertionSetId}
            taxonomyVersion={assertions.taxonomyVersion}
            onSelectSet={(value) =>
              onChangeQuery({ assertionSetId: value, offset: 0 })
            }
          />
          <AssertionFilters
            query={query}
            taxonomy={taxonomy}
            sources={sources}
            onChange={onChangeQuery}
          />

          {isLoading && <p role="status">Loading scope assertions…</p>}

          {!isLoading && items.length === 0 ? (
            <p className="preconstruction-empty">
              No scope assertions match the current filters. Run scope
              extraction on a prepared review set, or add a human-authored
              assertion.
            </p>
          ) : (
            <ul className="assertion-list">
              {items.map((assertion) => (
                <div key={assertion.id}>
                  <AssertionListItem
                    assertion={assertion}
                    selected={expandedId === assertion.id}
                    onSelect={toggle}
                    onReview={onReview}
                  />
                  {expandedId === assertion.id && (
                    <AssertionDetailPanel
                      assertion={assertion}
                      onNavigate={onNavigate}
                      onInspect={onInspect}
                    />
                  )}
                </div>
              ))}
            </ul>
          )}

          <div className="assertion-pagination">
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
    </Card>
  );
}

export default ScopeAssertionWorkspace;
