import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";

function InspectionsPage({
  projectName,
  inspections,
  inspectionDate,
  inspectionType,
  inspectionStatus,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onCreate,
  onDateChange,
  onTypeChange,
  onStatusChange,
  isCreating = false,
  isRefreshing = false,
  isLoading = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const filteredInspections = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return inspections.filter((inspection) => {
      const matchesStatus =
        !statusFilter || inspection.status === statusFilter;
      const matchesQuery =
        !query ||
        String(inspection.inspection_type || "")
          .toLowerCase()
          .includes(query);

      return matchesStatus && matchesQuery;
    });
  }, [inspections, searchQuery, statusFilter]);

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="inspections"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Inspections"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            <Icon name="refresh" size={17} />
            {isRefreshing ? "Refreshing inspections…" : "Refresh Inspections"}
          </Button>
        }
      />

      <Card
        as="form"
        title="Create Inspection"
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <FormField label="Date" htmlFor="inspection-date" required>
          <input
            id="inspection-date"
            className="field-control"
            type="date"
            required
            value={inspectionDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>
        <FormField label="Inspection" htmlFor="inspection-type" required>
          <input
            id="inspection-type"
            className="field-control"
            required
            value={inspectionType}
            onChange={(event) => onTypeChange(event.target.value)}
          />
        </FormField>
        <FormField label="Status" htmlFor="inspection-status">
          <select
            id="inspection-status"
            className="field-control"
            value={inspectionStatus}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            <option value="Pending">Pending</option>
            <option value="Pass">Pass</option>
            <option value="Partial Pass">Partial Pass</option>
            <option value="Fail">Fail</option>
          </select>
        </FormField>

        <Button
          type="submit"
          variant="primary"
          disabled={isCreating}
          aria-busy={isCreating}
        >
          {isCreating ? "Saving inspection…" : "Save Inspection"}
        </Button>
      </Card>

      <RecordFilters resultCount={filteredInspections.length}>
        <FormField label="Search" htmlFor="inspection-search">
          <input
            id="inspection-search"
            className="field-control"
            type="search"
            placeholder="Inspection name"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </FormField>
        <FormField label="Status" htmlFor="inspection-status-filter">
          <select
            id="inspection-status-filter"
            className="field-control"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="Pending">Pending</option>
            <option value="Pass">Pass</option>
            <option value="Partial Pass">Partial Pass</option>
            <option value="Fail">Fail</option>
          </select>
        </FormField>
      </RecordFilters>

      <RecordTable
        label="Inspections"
        isLoading={isLoading}
        loadingMessage="Loading inspections…"
        emptyMessage={
          inspections.length
            ? "No inspections match the current filters."
            : "No inspections yet. Create the first inspection above."
        }
        headers={["Date", "Inspection", "Status"]}
      >
        {filteredInspections.map((inspection) => (
          <tr key={inspection.id}>
            <RecordCell label="Date">{formatDate(inspection.date)}</RecordCell>
            <RecordCell label="Inspection">
              {inspection.inspection_type}
            </RecordCell>
            <RecordCell label="Status">
              <StatusBadge value={inspection.status} />
            </RecordCell>
          </tr>
        ))}
      </RecordTable>
    </ProjectLayout>
  );
}

export default InspectionsPage;
