import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";

function NotesDelaysPage({
  projectName,
  notesDelays,
  projectCompanies,
  noteDelayDate,
  noteDelayType,
  noteDelayCompany,
  noteDelayDescription,
  noteDelayImpact,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onCreate,
  onDateChange,
  onTypeChange,
  onCompanyChange,
  onDescriptionChange,
  onImpactChange,
  isCreating = false,
  isRefreshing = false,
  isLoading = false,
  isLoadingCompanies = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");

  const filteredEntries = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return notesDelays.filter((entry) => {
      const matchesType = !typeFilter || entry.entry_type === typeFilter;
      const matchesCompany =
        !companyFilter || entry.company === companyFilter;
      const matchesQuery =
        !query ||
        [entry.company, entry.description, entry.impact].some((value) =>
          String(value || "").toLowerCase().includes(query)
        );

      return matchesType && matchesCompany && matchesQuery;
    });
  }, [companyFilter, notesDelays, searchQuery, typeFilter]);

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="notesDelays"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Notes & Delays"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            {isRefreshing ? "Refreshing entries…" : "Refresh Entries"}
          </Button>
        }
      />

      <Card
        as="form"
        title="Create Entry"
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <FormField label="Date" htmlFor="note-delay-date" required>
          <input
            id="note-delay-date"
            className="field-control"
            type="date"
            required
            value={noteDelayDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>
        <FormField label="Entry type" htmlFor="note-delay-type">
          <select
            id="note-delay-type"
            className="field-control"
            value={noteDelayType}
            onChange={(event) => onTypeChange(event.target.value)}
          >
            <option value="Note">Note</option>
            <option value="Delay">Delay</option>
          </select>
        </FormField>
        <FormField label="Company" htmlFor="note-delay-company">
          <select
            id="note-delay-company"
            className="field-control"
            value={noteDelayCompany}
            disabled={isLoadingCompanies}
            onChange={(event) => onCompanyChange(event.target.value)}
          >
            <option value="">
              {isLoadingCompanies ? "Loading companies…" : "Select company"}
            </option>
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name}>
                {company.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Description" htmlFor="note-delay-description" required>
          <textarea
            id="note-delay-description"
            className="field-control"
            required
            value={noteDelayDescription}
            onChange={(event) => onDescriptionChange(event.target.value)}
          />
        </FormField>
        <FormField label="Impact" htmlFor="note-delay-impact">
          <textarea
            id="note-delay-impact"
            className="field-control"
            value={noteDelayImpact}
            onChange={(event) => onImpactChange(event.target.value)}
          />
        </FormField>

        <Button
          type="submit"
          variant="primary"
          disabled={isCreating}
          aria-busy={isCreating}
        >
          {isCreating ? "Saving entry…" : "Save Entry"}
        </Button>
      </Card>

      <RecordFilters resultCount={filteredEntries.length}>
        <FormField label="Search" htmlFor="notes-delays-search">
          <input
            id="notes-delays-search"
            className="field-control"
            type="search"
            placeholder="Company, description, or impact"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </FormField>
        <FormField label="Type" htmlFor="notes-delays-type-filter">
          <select
            id="notes-delays-type-filter"
            className="field-control"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
          >
            <option value="">All types</option>
            <option value="Note">Notes</option>
            <option value="Delay">Delays</option>
          </select>
        </FormField>
        <FormField label="Company" htmlFor="notes-delays-company-filter">
          <select
            id="notes-delays-company-filter"
            className="field-control"
            value={companyFilter}
            disabled={isLoadingCompanies}
            onChange={(event) => setCompanyFilter(event.target.value)}
          >
            <option value="">All companies</option>
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name}>
                {company.name}
              </option>
            ))}
          </select>
        </FormField>
      </RecordFilters>

      <RecordTable
        label="Notes and delays"
        isLoading={isLoading}
        loadingMessage="Loading notes and delays…"
        emptyMessage={
          notesDelays.length
            ? "No notes or delays match the current filters."
            : "No notes or delays yet. Create the first entry above."
        }
        headers={["Date", "Type", "Company", "Description", "Impact"]}
      >
        {filteredEntries.map((entry) => (
          <tr key={entry.id}>
            <RecordCell label="Date">{formatDate(entry.date)}</RecordCell>
            <RecordCell label="Type">
              <StatusBadge value={entry.entry_type} />
            </RecordCell>
            <RecordCell label="Company">{entry.company}</RecordCell>
            <RecordCell label="Description">{entry.description}</RecordCell>
            <RecordCell label="Impact">{entry.impact}</RecordCell>
          </tr>
        ))}
      </RecordTable>
    </ProjectLayout>
  );
}

export default NotesDelaysPage;
