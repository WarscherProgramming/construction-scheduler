import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";

function DailyLogsPage({
  projectName,
  dailyLogs,
  projectCompanies,
  logDate,
  logCompany,
  logManpower,
  logNotes,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onCreate,
  onDateChange,
  onCompanyChange,
  onManpowerChange,
  onNotesChange,
  isCreating = false,
  isRefreshing = false,
  isLoading = false,
  isLoadingCompanies = false,
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
    <ProjectLayout
      projectName={projectName}
      activeId="dailyLogs"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Daily Logs"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            {isRefreshing ? "Refreshing logs…" : "Refresh Logs"}
          </Button>
        }
      />

      <Card
        as="form"
        title="Create Daily Log"
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
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
            disabled={isLoadingCompanies}
            value={logCompany}
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

        <Button
          type="submit"
          variant="primary"
          disabled={isCreating}
          aria-busy={isCreating}
        >
          {isCreating ? "Saving daily log…" : "Save Daily Log"}
        </Button>
      </Card>

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
        label="Daily logs"
        isLoading={isLoading}
        loadingMessage="Loading daily logs…"
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
    </ProjectLayout>
  );
}

export default DailyLogsPage;
