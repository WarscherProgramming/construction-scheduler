import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import { buttonStyle, tableCellStyle } from "../styles";

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
  onBack,
  onRefresh,
  onCreate,
  onDateChange,
  onTypeChange,
  onCompanyChange,
  onDescriptionChange,
  onImpactChange,
  isCreating = false,
  isRefreshing = false,
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
    <ProjectPageLayout title={`${projectName} Notes & Delays`} onBack={onBack}>
      <form
        className="form-stack form-card"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <h3>Create Entry</h3>

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
            onChange={(event) => onCompanyChange(event.target.value)}
          >
            <option value="">Select company</option>
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

        <button
          type="submit"
          className="button-primary"
          disabled={isCreating}
          aria-busy={isCreating}
          style={buttonStyle}
        >
          {isCreating ? "Saving entry…" : "Save Entry"}
        </button>
      </form>

      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-busy={isRefreshing}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        {isRefreshing ? "Refreshing entries…" : "Refresh Entries"}
      </button>

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
        emptyMessage={
          notesDelays.length
            ? "No notes or delays match the current filters."
            : "No notes or delays yet. Create the first entry above."
        }
        headers={["Date", "Type", "Company", "Description", "Impact"]}
      >
        {filteredEntries.map((entry) => (
          <tr key={entry.id}>
            <td style={tableCellStyle}>{formatDate(entry.date)}</td>
            <td style={tableCellStyle}>
              <StatusBadge value={entry.entry_type} />
            </td>
            <td style={tableCellStyle}>{entry.company}</td>
            <td style={tableCellStyle}>{entry.description}</td>
            <td style={tableCellStyle}>{entry.impact}</td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default NotesDelaysPage;
