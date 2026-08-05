import { useMemo, useState } from "react";

import { formatDisplayDate } from "../../utils/date";
import EmptyState from "../EmptyState";
import LoadingState from "../LoadingState";
import StatusBadge from "../StatusBadge";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import CreateLookAheadDialog from "./CreateLookAheadDialog";
import LookAheadItemDialog from "./LookAheadItemDialog";


function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}


function allItems(detail) {
  if (!detail) return [];
  return [
    ...detail.carryover_items,
    ...detail.weeks.flatMap((week) => week.items),
    ...detail.manual_items,
    ...detail.excluded_items,
  ];
}


function matchesFilters(item, filters) {
  const haystack = [
    item.wbs,
    item.name,
    item.blocking_reason,
    item.commitment_note,
    item.constraint_owner,
    item.responsible_company?.name,
    item.responsible_company?.trade,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (filters.search && !haystack.includes(filters.search.toLowerCase())) return false;
  if (filters.readiness && item.readiness_status !== filters.readiness) return false;
  if (filters.progress && item.progress_status !== filters.progress) return false;
  if (filters.companyId && item.responsible_company?.id !== Number(filters.companyId)) return false;
  if (filters.criticalOnly && !item.is_critical) return false;
  if (filters.milestonesOnly && !item.is_milestone) return false;
  if (filters.blockedOnly && !item.blocked) return false;
  if (filters.overdueOnly && !item.overdue) return false;
  if (filters.outOfSequenceOnly && !item.out_of_sequence) return false;
  return true;
}


function LookAheadItemCard({ item, readOnly, onEdit, onProgress, onPlanning }) {
  return (
    <article className="look-ahead-item">
      <div className="look-ahead-item__header">
        <div>
          <p className="look-ahead-item__eyebrow">
            {item.wbs ? `Task ${item.wbs}` : `Task ${item.task_id}`}
            {item.manually_included ? " · Manually included" : ""}
          </p>
          <h4>{item.name || "Task no longer available"}</h4>
        </div>
        <StatusBadge value={titleCase(item.readiness_status)} />
      </div>
      {!item.task_available ? (
        <p className="look-ahead-item__unavailable">
          The live schedule task was removed. Persisted planning metadata is retained.
        </p>
      ) : (
        <>
          <dl className="look-ahead-item__facts">
            <div><dt>Forecast</dt><dd>{formatDisplayDate(item.start_date)} to {formatDisplayDate(item.end_date)}</dd></div>
            <div><dt>Progress</dt><dd>{titleCase(item.progress_status)} · {item.percent_complete}%</dd></div>
            <div><dt>Company / Trade</dt><dd>{item.responsible_company ? `${item.responsible_company.name}${item.responsible_company.trade ? ` / ${item.responsible_company.trade}` : ""}` : "Unassigned"}</dd></div>
            <div><dt>Schedule Facts</dt><dd>{item.is_milestone ? "Milestone" : `${item.predecessor_count} predecessor${item.predecessor_count === 1 ? "" : "s"}`}{item.is_critical ? " · Critical" : ""}{item.constraint_type && item.constraint_type !== "ASAP" ? ` · ${item.constraint_type}` : ""}</dd></div>
          </dl>
          <div className="look-ahead-item__labels" aria-label="Attention states">
            {item.overdue && <span>Overdue</span>}
            {item.blocked && <span>Blocked</span>}
            {item.out_of_sequence && <span>Out of Sequence</span>}
            {item.constraint_due && <span>Blocker Resolution Due</span>}
            {item.commitment_missing && <span>Commitment Missing</span>}
            {item.spans_multiple_weeks && <span>Spans Multiple Weeks</span>}
          </div>
        </>
      )}
      {(item.blocking_reason || item.commitment_note || item.override_reason) && (
        <dl className="look-ahead-item__notes">
          {item.blocking_reason && <div><dt>Blocker</dt><dd>{item.blocking_reason}</dd></div>}
          {item.commitment_note && <div><dt>Commitment</dt><dd>{item.commitment_note}</dd></div>}
          {item.override_reason && <div><dt>Override</dt><dd>{item.override_reason}</dd></div>}
        </dl>
      )}
      {!readOnly && item.task_available && (
        <div className="look-ahead-item__actions">
          <Button size="sm" onClick={() => onEdit(item)}>Edit Item</Button>
          <Button size="sm" onClick={() => onProgress(item.task_id)}>Update Progress</Button>
          <Button size="sm" onClick={() => onPlanning(item.task_id)}>Edit CPM Planning</Button>
        </div>
      )}
    </article>
  );
}


function LookAheadGroup({ title, description, items, ...itemProps }) {
  return (
    <section className="look-ahead-group" aria-labelledby={`look-ahead-${title.replaceAll(" ", "-").toLowerCase()}`}>
      <div className="look-ahead-group__header">
        <div>
          <h3 id={`look-ahead-${title.replaceAll(" ", "-").toLowerCase()}`}>{title}</h3>
          {description && <p>{description}</p>}
        </div>
        <span>{items.length} {items.length === 1 ? "item" : "items"}</span>
      </div>
      {items.length ? (
        <div className="look-ahead-item-list">
          {items.map((item) => <LookAheadItemCard key={item.task_id} item={item} {...itemProps} />)}
        </div>
      ) : (
        <p className="look-ahead-group__empty">No matching work in this period.</p>
      )}
    </section>
  );
}


function LookAheadPlanningView({
  lookAhead,
  tasks,
  companies,
  dataDate,
  onOpenProgress,
  onOpenPlanning,
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [candidateTaskId, setCandidateTaskId] = useState("");
  const [archiveOpen, setArchiveOpen] = useState(false);
  const detail = lookAhead.detail;
  const selectedPlan = lookAhead.selectedPlan;
  const readOnly = selectedPlan?.status === "archived";
  const visibleTaskIds = useMemo(
    () => new Set(allItems(detail).map((item) => item.task_id)),
    [detail]
  );
  const parentIds = useMemo(
    () => new Set(tasks.map((task) => task.parent_task_id).filter(Boolean)),
    [tasks]
  );
  const candidates = tasks.filter(
    (task) => !parentIds.has(task.id) && !visibleTaskIds.has(task.id)
  );
  const filtered = (items, section, weekIndex = null) => {
    if (lookAhead.filters.week) {
      const selected = lookAhead.filters.week;
      if (selected === "carryover" && section !== "carryover") return [];
      if (selected === "manual" && section !== "manual") return [];
      if (selected === "excluded" && section !== "excluded") return [];
      if (/^\d+$/.test(selected) && Number(selected) !== weekIndex) return [];
    }
    return items.filter((item) => matchesFilters(item, lookAhead.filters));
  };

  const candidate = candidates.find((task) => task.id === Number(candidateTaskId));
  const candidateItem = candidate
    ? {
        ...candidate,
        task_id: candidate.id,
        task_available: true,
        wbs: null,
        readiness_status: "unreviewed",
        responsible_company: null,
        manually_included: true,
        manually_excluded: false,
      }
    : null;

  return (
    <div className="look-ahead-planning">
      {createOpen && (
        <CreateLookAheadDialog
          open
          dataDate={dataDate}
          isSubmitting={lookAhead.isCreating}
          serverError={lookAhead.mutationError}
          onSubmit={lookAhead.createPlan}
          onCancel={() => setCreateOpen(false)}
          onClearError={lookAhead.clearMutationError}
        />
      )}
      {editingItem && (
        <LookAheadItemDialog
          key={`${selectedPlan?.id}:${editingItem.task_id}`}
          item={editingItem}
          companies={companies}
          isCandidate={Boolean(editingItem.__candidate)}
          isSubmitting={lookAhead.isUpdatingItem}
          onSubmit={(taskId, payload) => lookAhead.updateItem(selectedPlan.id, taskId, payload)}
          onCancel={() => setEditingItem(null)}
        />
      )}
      <ConfirmDialog
        open={archiveOpen}
        title="Archive Look-Ahead Plan?"
        message="The plan will remain viewable, but its readiness, blockers, commitments, and overrides can no longer be edited."
        confirmLabel="Archive Plan"
        confirmDisabled={lookAhead.isArchiving}
        onConfirm={async () => {
          const result = await lookAhead.archivePlan(selectedPlan.id);
          if (result) setArchiveOpen(false);
        }}
        onCancel={() => setArchiveOpen(false)}
      />

      <div className="look-ahead-plan-bar no-print">
        <div className="field-group">
          <label className="field-label" htmlFor="look-ahead-plan-selector">Look-Ahead Plan</label>
          <select
            id="look-ahead-plan-selector"
            className="field-control"
            value={lookAhead.selectedPlanId || ""}
            disabled={lookAhead.isLoadingList}
            onChange={(event) => void lookAhead.selectPlan(event.target.value)}
          >
            <option value="">Select a plan</option>
            {lookAhead.plans.map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name} · {formatDisplayDate(plan.anchor_date)} · {titleCase(plan.status)}
              </option>
            ))}
          </select>
        </div>
        <div className="look-ahead-plan-actions">
          <Button variant="primary" onClick={() => setCreateOpen(true)}>Create Plan</Button>
          <Button disabled={!detail} onClick={() => window.print()}>Print Plan</Button>
          <Button disabled={!selectedPlan || readOnly} onClick={() => setArchiveOpen(true)}>Archive</Button>
        </div>
      </div>

      {lookAhead.listError ? (
        <div className="schedule-load-error" role="alert">
          <p>Look-ahead plans could not be loaded.</p>
          <Button onClick={lookAhead.retryPlans}>Retry</Button>
        </div>
      ) : lookAhead.isLoadingList ? (
        <LoadingState message="Loading look-ahead plans..." />
      ) : !lookAhead.plans.length ? (
        <EmptyState title="No look-ahead plans yet" description="Create a plan to organize live schedule work into a bounded field-planning window." />
      ) : lookAhead.detailError ? (
        <div className="schedule-load-error" role="alert">
          <p>The selected look-ahead plan could not be loaded.</p>
          <Button onClick={lookAhead.retryDetail}>Retry</Button>
        </div>
      ) : lookAhead.isLoadingDetail || !detail ? (
        <LoadingState message="Loading selected look-ahead plan..." />
      ) : (
        <>
          <header className="look-ahead-header">
            <div>
              <p className="look-ahead-header__eyebrow">{titleCase(detail.plan.status)} Look-Ahead Plan</p>
              <h2>{detail.plan.name}</h2>
              {detail.plan.description && <p>{detail.plan.description}</p>}
            </div>
            <dl>
              <div><dt>Planning Window</dt><dd>{formatDisplayDate(detail.plan.anchor_date)} to {formatDisplayDate(detail.window_end_date)}</dd></div>
              <div><dt>Data Date</dt><dd>{formatDisplayDate(detail.current_data_date)}</dd></div>
              <div><dt>Duration</dt><dd>{detail.plan.window_days} calendar days</dd></div>
            </dl>
          </header>

          <section className="look-ahead-summary" aria-label="Look-ahead summary">
            {[
              ["Total", detail.summary.total_items],
              ["Carryover", detail.summary.carryover_count],
              ["Ready", detail.summary.ready_count],
              ["At Risk", detail.summary.at_risk_count],
              ["Blocked", detail.summary.blocked_count],
              ["Committed", detail.summary.committed_count],
              ["Overdue", detail.summary.overdue_count],
              ["Critical", detail.summary.critical_count],
              ["Milestones", detail.summary.milestones_count],
            ].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
          </section>

          <section className="look-ahead-filters no-print" aria-labelledby="look-ahead-filters-title">
            <div className="look-ahead-filter-heading">
              <h3 id="look-ahead-filters-title">Filters</h3>
              <Button size="sm" onClick={lookAhead.clearFilters}>Clear Filters</Button>
            </div>
            <div className="look-ahead-filter-grid">
              <label>Search<input className="field-control" type="search" value={lookAhead.filters.search} onChange={(event) => lookAhead.updateFilters({ search: event.target.value })} /></label>
              <label>Period<select className="field-control" value={lookAhead.filters.week} onChange={(event) => lookAhead.updateFilters({ week: event.target.value })}><option value="">All periods</option><option value="carryover">Carryover</option>{detail.weeks.map((week) => <option key={week.week_index} value={week.week_index}>Week {week.week_index}</option>)}<option value="manual">Manual</option><option value="excluded">Excluded</option></select></label>
              <label>Readiness<select className="field-control" value={lookAhead.filters.readiness} onChange={(event) => lookAhead.updateFilters({ readiness: event.target.value })}><option value="">All readiness</option>{["unreviewed", "ready", "at_risk", "blocked", "committed", "complete"].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label>
              <label>Progress<select className="field-control" value={lookAhead.filters.progress} onChange={(event) => lookAhead.updateFilters({ progress: event.target.value })}><option value="">All progress</option>{["not_started", "in_progress", "completed"].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label>
              <label>Company / Trade<select className="field-control" value={lookAhead.filters.companyId} onChange={(event) => lookAhead.updateFilters({ companyId: event.target.value })}><option value="">All companies</option>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}{company.trade ? ` - ${company.trade}` : ""}</option>)}</select></label>
            </div>
            <div className="look-ahead-filter-toggles">
              {[["criticalOnly", "Critical only"], ["milestonesOnly", "Milestones only"], ["blockedOnly", "Blocked only"], ["overdueOnly", "Overdue only"], ["outOfSequenceOnly", "Out of sequence only"]].map(([key, label]) => <label key={key}><input type="checkbox" checked={lookAhead.filters[key]} onChange={(event) => lookAhead.updateFilters({ [key]: event.target.checked })} /> {label}</label>)}
            </div>
          </section>

          {!readOnly && (
            <section className="look-ahead-manual-add no-print" aria-labelledby="look-ahead-manual-title">
              <div><h3 id="look-ahead-manual-title">Manual Inclusion</h3><p>Add an out-of-window or unscheduled leaf task without changing its schedule dates.</p></div>
              <div className="look-ahead-manual-add__controls">
                <select className="field-control" aria-label="Task to include" value={candidateTaskId} onChange={(event) => setCandidateTaskId(event.target.value)}><option value="">Select a task</option>{candidates.map((task) => <option key={task.id} value={task.id}>{task.name || `Task ${task.id}`}</option>)}</select>
                <Button disabled={!candidateItem} onClick={() => setEditingItem({ ...candidateItem, __candidate: true })}>Include Task</Button>
              </div>
            </section>
          )}

          <div className="look-ahead-groups">
            <LookAheadGroup title="Carryover / Overdue" description="Incomplete work that began or should have finished before the planning anchor." items={filtered(detail.carryover_items, "carryover")} readOnly={readOnly} onEdit={setEditingItem} onProgress={onOpenProgress} onPlanning={onOpenPlanning} />
            {detail.weeks.map((week) => <LookAheadGroup key={week.week_index} title={`Week ${week.week_index}`} description={`${formatDisplayDate(week.start_date)} to ${formatDisplayDate(week.end_date)}`} items={filtered(week.items, "week", week.week_index)} readOnly={readOnly} onEdit={setEditingItem} onProgress={onOpenProgress} onPlanning={onOpenPlanning} />)}
            {(detail.manual_items.length > 0 || lookAhead.filters.week === "manual") && <LookAheadGroup title="Manual / Unscheduled" description="Controlled inclusions outside the automatic planning window." items={filtered(detail.manual_items, "manual")} readOnly={readOnly} onEdit={setEditingItem} onProgress={onOpenProgress} onPlanning={onOpenPlanning} />}
            {(detail.excluded_items.length > 0 || lookAhead.filters.week === "excluded") && <LookAheadGroup title="Excluded Items" description="Tasks explicitly removed from this planning cycle without changing the live schedule." items={filtered(detail.excluded_items, "excluded")} readOnly={readOnly} onEdit={setEditingItem} onProgress={onOpenProgress} onPlanning={onOpenPlanning} />}
          </div>
        </>
      )}
    </div>
  );
}


export default LookAheadPlanningView;
