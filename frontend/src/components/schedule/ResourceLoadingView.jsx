import { useEffect, useMemo, useState } from "react";

import { formatDisplayDate } from "../../utils/date";
import EmptyState from "../EmptyState";
import LoadingState from "../LoadingState";
import StatusBadge from "../StatusBadge";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import ResourceAvailabilityDialog from "./ResourceAvailabilityDialog";


const EMPTY_CREW = {
  name: "",
  trade: "",
  company_id: "",
  description: "",
  default_capacity: "1",
};
const EMPTY_EQUIPMENT = {
  name: "",
  equipment_type: "",
  identifier: "",
  description: "",
  default_capacity: "1",
};


function ResourceForm({ type, value, companies, pending, onChange, onSubmit, onCancel }) {
  const isCrew = type === "crew";
  return (
    <form className="resource-management-form" onSubmit={onSubmit}>
      <div className="resource-form-grid">
        <label>Name<input className="field-control" value={value.name} maxLength="120" required onChange={(event) => onChange({ ...value, name: event.target.value })} /></label>
        {isCrew ? (
          <label>Trade<input className="field-control" value={value.trade} maxLength="255" onChange={(event) => onChange({ ...value, trade: event.target.value })} /></label>
        ) : (
          <>
            <label>Equipment type<input className="field-control" value={value.equipment_type} maxLength="120" required onChange={(event) => onChange({ ...value, equipment_type: event.target.value })} /></label>
            <label>Identifier<input className="field-control" value={value.identifier} maxLength="120" onChange={(event) => onChange({ ...value, identifier: event.target.value })} /></label>
          </>
        )}
        {isCrew && (
          <label>Company<select className="field-control" value={value.company_id} onChange={(event) => onChange({ ...value, company_id: event.target.value })}><option value="">No company</option>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>
        )}
        <label>Default capacity ({isCrew ? "workers" : "units"})<input className="field-control" type="number" min="1" max="1000000" step="1" value={value.default_capacity} required onChange={(event) => onChange({ ...value, default_capacity: event.target.value })} /></label>
      </div>
      <label>Description<textarea className="field-control" maxLength="2000" value={value.description} onChange={(event) => onChange({ ...value, description: event.target.value })} /></label>
      <div className="resource-inline-actions">
        {onCancel && <Button type="button" onClick={onCancel}>Cancel Edit</Button>}
        <Button type="submit" variant="primary" disabled={pending}>{pending ? "Saving..." : onCancel ? "Save Changes" : `Add ${isCrew ? "Crew" : "Equipment"}`}</Button>
      </div>
    </form>
  );
}


function ResourceManagement({ type, resources, companies, onLoadingChanged }) {
  const isCrew = type === "crew";
  const rows = isCrew ? resources.crews : resources.equipment;
  const empty = isCrew ? EMPTY_CREW : EMPTY_EQUIPMENT;
  const [form, setForm] = useState({ ...empty });
  const [editing, setEditing] = useState(null);
  const [availabilityResource, setAvailabilityResource] = useState(null);
  const [archiveResource, setArchiveResource] = useState(null);
  const pending = resources.isPending(isCrew ? "create-crew" : "create-equipment") ||
    resources.isPending(isCrew ? "update-crew" : "update-equipment");

  const reset = () => {
    setEditing(null);
    setForm({ ...empty });
  };

  const submit = async (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      default_capacity: Number(form.default_capacity),
      description: form.description.trim() || null,
      ...(isCrew
        ? { trade: form.trade.trim() || null, company_id: form.company_id ? Number(form.company_id) : null }
        : { identifier: form.identifier.trim() || null }),
    };
    const result = editing
      ? isCrew
        ? await resources.updateCrew(editing.id, payload)
        : await resources.updateEquipment(editing.id, payload)
      : isCrew
        ? await resources.createCrew(payload)
        : await resources.createEquipment(payload);
    if (result) {
      reset();
      await onLoadingChanged();
    }
  };

  const archive = async () => {
    const target = archiveResource;
    setArchiveResource(null);
    if (!target) return;
    const result = isCrew
      ? await resources.archiveCrew(target.id)
      : await resources.archiveEquipment(target.id);
    if (result) await onLoadingChanged();
  };

  return (
    <section className="resource-management" aria-labelledby={`${type}-resources-title`}>
      <div className="resource-section-heading">
        <div><h2 id={`${type}-resources-title`}>{isCrew ? "Labor Crews" : "Equipment Resources"}</h2><p>Manage default workday capacity and dated availability without changing task dates.</p></div>
        <span>{rows.filter((row) => row.status === "active").length} active</span>
      </div>
      <ResourceForm type={type} value={form} companies={companies} pending={pending} onChange={setForm} onSubmit={submit} onCancel={editing ? reset : null} />
      {resources.isLoading ? <LoadingState message={`Loading ${isCrew ? "crews" : "equipment"}...`} /> : rows.length ? (
        <div className="resource-record-list">
          {rows.map((row) => (
            <article key={row.id} className="resource-record">
              <div>
                <div className="resource-record__title"><h3>{row.name}</h3><StatusBadge value={row.status} /></div>
                <p>{isCrew ? row.trade || "Trade not set" : row.equipment_type}{!isCrew && row.identifier ? ` / ${row.identifier}` : ""}</p>
                {isCrew && row.company && <p>{row.company.name}</p>}
                <strong>{row.default_capacity} {row.capacity_unit} default capacity</strong>
              </div>
              <div className="resource-inline-actions">
                <Button size="sm" onClick={() => setAvailabilityResource(row)}>Availability</Button>
                {row.status === "active" && <Button size="sm" onClick={() => {
                  setEditing(row);
                  setForm(isCrew ? {
                    name: row.name,
                    trade: row.trade || "",
                    company_id: row.company?.id ? String(row.company.id) : "",
                    description: row.description || "",
                    default_capacity: String(row.default_capacity),
                  } : {
                    name: row.name,
                    equipment_type: row.equipment_type,
                    identifier: row.identifier || "",
                    description: row.description || "",
                    default_capacity: String(row.default_capacity),
                  });
                }}>Edit</Button>}
                {row.status === "active" && <Button size="sm" variant="danger" onClick={() => setArchiveResource(row)}>Archive</Button>}
              </div>
            </article>
          ))}
        </div>
      ) : <EmptyState title={`No ${isCrew ? "crews" : "equipment"} yet`} description={`Add the first ${isCrew ? "labor crew" : "equipment resource"} above.`} />}
      {availabilityResource && <ResourceAvailabilityDialog resource={availabilityResource} resourceType={type} resources={resources} onChanged={onLoadingChanged} onCancel={() => setAvailabilityResource(null)} />}
      <ConfirmDialog open={Boolean(archiveResource)} destructive title={`Archive ${archiveResource?.name || "resource"}?`} message="Existing assignments remain factual, but this resource cannot be changed or newly assigned." confirmLabel="Archive" onConfirm={archive} onCancel={() => setArchiveResource(null)} />
    </section>
  );
}


function LoadingResults({ data }) {
  if (!data.resources.length && !data.unassigned_tasks.length) {
    return <EmptyState title="No resource loading in this window" description="Add active resources and task assignments, or adjust the date range." />;
  }
  return (
    <>
      <section className="resource-summary-grid" aria-label="Resource loading summary">
        {[
          ["Active Crews", data.summary.active_crews],
          ["Active Equipment", data.summary.active_equipment_resources],
          ["Assigned Tasks", data.summary.assigned_tasks],
          ["Unassigned Tasks", data.summary.unassigned_executable_tasks],
          ["Conflict Days", data.summary.over_allocated_resource_days],
          ["Unavailable Conflicts", data.summary.unavailable_resource_conflicts],
          ["Peak Labor", `${data.summary.peak_labor_demand} workers`],
          ["Average Labor", `${data.summary.average_labor_demand} workers/day`],
        ].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </section>
      <div className="resource-loading-table-wrap" role="region" aria-label="Resource loading by workday" tabIndex="0">
        <table className="resource-loading-table">
          <caption className="visually-hidden">Demand and capacity for each resource by date</caption>
          <thead><tr><th scope="col">Resource</th>{data.resources[0]?.days.map((day) => <th scope="col" key={day.date}>{formatDisplayDate(day.date)}</th>)}</tr></thead>
          <tbody>{data.resources.map((row) => <tr key={`${row.resource.resource_type}:${row.resource.id}`}><th scope="row"><strong>{row.resource.name}</strong><span>{row.resource.detail || row.resource.resource_type}</span></th>{row.days.map((day) => <td key={day.date} className={`resource-load-cell resource-load-cell--${day.status}`} aria-label={`${row.resource.name}, ${formatDisplayDate(day.date)}: demand ${day.demand}, capacity ${day.capacity}, ${day.utilization_percent == null ? "utilization unavailable" : `${day.utilization_percent}% utilized`}, ${day.status.replaceAll("_", " ")}`}><strong>{day.demand}/{day.capacity}</strong><span>{day.utilization_percent == null ? "No capacity" : `${day.utilization_percent}%`}</span>{day.status !== "within_capacity" && <span>{day.status === "unavailable" ? "Unavailable" : `Over by ${day.overage}`}</span>}</td>)}</tr>)}</tbody>
        </table>
      </div>
      {data.conflicts.length > 0 && <section className="resource-conflicts" aria-labelledby="resource-conflicts-title"><h2 id="resource-conflicts-title">Capacity Conflicts</h2>{data.conflicts_truncated && <p>Showing {data.conflicts.length} of {data.total_conflicts} conflict days. Narrow the date range or filters to review more.</p>}<ul>{data.conflicts.map((conflict) => <li key={`${conflict.resource.resource_type}:${conflict.resource.id}:${conflict.date}`}><strong>{conflict.resource.name} / {formatDisplayDate(conflict.date)}</strong><span>{conflict.message}</span><small>{conflict.contributing_tasks.map((task) => `${task.wbs || task.id} ${task.name}`).join(", ")}{conflict.contributing_tasks_truncated ? ` and ${conflict.contributing_task_count - conflict.contributing_tasks.length} more` : ""}</small></li>)}</ul></section>}
      {data.summary.equipment_type_peaks.length > 0 && <section className="resource-equipment-peaks" aria-labelledby="equipment-peaks-title"><h2 id="equipment-peaks-title">Peak Equipment Demand</h2><ul>{data.summary.equipment_type_peaks.map((item) => <li key={item.equipment_type}><span>{item.equipment_type}</span><strong>{item.peak_demand} units</strong></li>)}</ul></section>}
      {data.unassigned_tasks.length > 0 && <section className="resource-unassigned" aria-labelledby="resource-unassigned-title"><h2 id="resource-unassigned-title">Unassigned Executable Tasks</h2><ul>{data.unassigned_tasks.map((task) => <li key={task.id}><strong>{task.wbs ? `${task.wbs} ` : ""}{task.name}</strong><span>{task.unscheduled ? "Unscheduled" : `${formatDisplayDate(task.start_date)} to ${formatDisplayDate(task.end_date)}`}</span></li>)}</ul></section>}
    </>
  );
}


function ResourceLoadingView({ resources, resourceLoading, companies = [] }) {
  const [section, setSection] = useState("loading");
  const [filters, setFilters] = useState({ startDate: "", endDate: "", resourceType: "", companyId: "", overAllocatedOnly: false, includeUnassigned: true });

  const loadResourceLoading = resourceLoading.load;
  useEffect(() => { void loadResourceLoading(); }, [loadResourceLoading]);
  const trades = useMemo(() => [...new Set(resources.crews.map((crew) => crew.trade).filter(Boolean))].sort(), [resources.crews]);
  const refreshLoading = async () => {
    if (resourceLoading.data) await resourceLoading.retry();
  };

  return (
    <div className="resource-planning-view">
      <div className="resource-subtabs no-print" role="group" aria-label="Resource planning sections">
        {[['loading', 'Loading'], ['crew', 'Crews'], ['equipment', 'Equipment']].map(([value, label]) => <Button key={value} aria-pressed={section === value} onClick={() => setSection(value)}>{label}</Button>)}
      </div>
      {section === "crew" ? <ResourceManagement type="crew" resources={resources} companies={companies} onLoadingChanged={refreshLoading} /> : section === "equipment" ? <ResourceManagement type="equipment" resources={resources} companies={companies} onLoadingChanged={refreshLoading} /> : (
        <>
          <header className="resource-loading-header"><div><h2>Live Resource Loading</h2><p>Forecast demand from the current schedule and Data Date. Conflicts are informational and do not move work.</p></div><Button className="no-print" onClick={() => window.print()}>Print</Button></header>
          <form className="resource-loading-filters no-print" onSubmit={(event) => { event.preventDefault(); void resourceLoading.load(filters); }}>
            <label>Start date<input className="field-control" type="date" value={filters.startDate} onChange={(event) => setFilters({ ...filters, startDate: event.target.value })} /></label>
            <label>End date<input className="field-control" type="date" value={filters.endDate} onChange={(event) => setFilters({ ...filters, endDate: event.target.value })} /></label>
            <label>Resource type<select className="field-control" value={filters.resourceType} onChange={(event) => setFilters({ ...filters, resourceType: event.target.value })}><option value="">All resources</option><option value="crew">Crews</option><option value="equipment">Equipment</option></select></label>
            <label>Company<select className="field-control" value={filters.companyId} disabled={filters.resourceType === "equipment"} onChange={(event) => setFilters({ ...filters, companyId: event.target.value })}><option value="">All companies</option>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>
            <label>Trade<select className="field-control" value={filters.trade || ""} disabled={filters.resourceType === "equipment"} onChange={(event) => setFilters({ ...filters, trade: event.target.value })}><option value="">All trades</option>{trades.map((trade) => <option key={trade} value={trade}>{trade}</option>)}</select></label>
            <label className="resource-filter-toggle"><input type="checkbox" checked={filters.overAllocatedOnly} onChange={(event) => setFilters({ ...filters, overAllocatedOnly: event.target.checked })} /> Conflicts only</label>
            <label className="resource-filter-toggle"><input type="checkbox" checked={filters.includeUnassigned} onChange={(event) => setFilters({ ...filters, includeUnassigned: event.target.checked })} /> Include unassigned tasks</label>
            <Button type="submit" variant="primary" disabled={resourceLoading.isLoading}>Apply</Button>
          </form>
          {resourceLoading.error ? <div className="schedule-load-error" role="alert"><p>Resource loading could not be displayed.</p><Button onClick={resourceLoading.retry}>Retry</Button></div> : resourceLoading.isLoading || !resourceLoading.data ? <LoadingState message="Calculating resource loading..." /> : <LoadingResults data={resourceLoading.data} />}
        </>
      )}
    </div>
  );
}


export default ResourceLoadingView;
