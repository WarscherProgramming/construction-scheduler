import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordCell from "../components/RecordCell";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import { buttonStyle } from "../styles";

function DailyLogsPage({
  projectName,
  dailyLogs,
  projectCompanies,
  logDate,
  logCompany,
  logManpower,
  logNotes,
  formatDate,
  onBack,
  onRefresh,
  onCreate,
  onDateChange,
  onCompanyChange,
  onManpowerChange,
  onNotesChange,
  isCreating = false,
  isRefreshing = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");

  const filteredLogs = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return dailyLogs.filter((log) => {
      const matchesCompany =
        !companyFilter || log.company === companyFilter;
      const matchesQuery =
        !query ||
        [log.company, log.notes, log.manpower].some((value) =>
          String(value || "").toLowerCase().includes(query)
        );

      return matchesCompany && matchesQuery;
    });
  }, [companyFilter, dailyLogs, searchQuery]);

  return (
    <ProjectPageLayout title={`${projectName} Daily Logs`} onBack={onBack}>
      <form
        className="form-stack form-card"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <h3>Create Daily Log</h3>

        <FormField label="Date" htmlFor="daily-log-date" required>
          <input
            id="daily-log-date"
            className="field-control"
            type="date"
            required
            value={logDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>

        <FormField label="Company" htmlFor="daily-log-company" required>
          <select
            id="daily-log-company"
            className="field-control"
            required
            value={logCompany}
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

        <FormField label="Manpower" htmlFor="daily-log-manpower" required>
          <select
            id="daily-log-manpower"
            className="field-control"
            required
            value={logManpower}
            onChange={(event) => onManpowerChange(event.target.value)}
          >
            <option value="">Select manpower</option>
            {Array.from({ length: 50 }, (_, index) => index + 1).map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Notes" htmlFor="daily-log-notes">
          <textarea
            id="daily-log-notes"
            className="field-control"
            value={logNotes}
            onChange={(event) => onNotesChange(event.target.value)}
          />
        </FormField>

        <button
          type="submit"
          className="button-primary"
          disabled={isCreating}
          aria-busy={isCreating}
          style={buttonStyle}
        >
          {isCreating ? "Saving daily log…" : "Save Daily Log"}
        </button>
      </form>

      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-busy={isRefreshing}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        {isRefreshing ? "Refreshing logs…" : "Refresh Logs"}
      </button>

      <RecordFilters resultCount={filteredLogs.length}>
        <FormField label="Search" htmlFor="daily-log-search">
          <input
            id="daily-log-search"
            className="field-control"
            type="search"
            placeholder="Company, notes, or manpower"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </FormField>
        <FormField label="Company" htmlFor="daily-log-company-filter">
          <select
            id="daily-log-company-filter"
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
        label="Daily logs"
        emptyMessage={
          dailyLogs.length
            ? "No daily logs match the current filters."
            : "No daily logs yet. Create the first log above."
        }
        headers={["Date", "Company", "Manpower", "Notes"]}
      >
        {filteredLogs.map((log) => (
          <tr key={log.id}>
            <RecordCell label="Date">{formatDate(log.date)}</RecordCell>
            <RecordCell label="Company">{log.company}</RecordCell>
            <RecordCell label="Manpower">{log.manpower}</RecordCell>
            <RecordCell label="Notes">{log.notes}</RecordCell>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default DailyLogsPage;
