import { useMemo, useState } from "react";

import AttachmentPanel from "../components/AttachmentPanel";
import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import RelationshipPanel from "../components/relationships/RelationshipPanel";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";

function DailyLogsPage({
  projectId,
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
  onAttachmentError,
  isCreating = false,
  isRefreshing = false,
  isLoading = false,
  isLoadingCompanies = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [attachmentLogId, setAttachmentLogId] = useState(null);
  const [relationshipLogId, setRelationshipLogId] = useState(null);

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

  const selectedLog = filteredLogs.find(
    (log) => log.id === attachmentLogId
  );
  const relationshipLog = filteredLogs.find(
    (log) => log.id === relationshipLogId
  );

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
            <Icon name="refresh" size={17} />
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
        headers={["Date", "Company", "Manpower", "Notes", "Actions"]}
      >
        {filteredLogs.map((log) => {
          const detailId = `daily-log-attachments-${log.id}`;
          const isExpanded = selectedLog?.id === log.id;
          const logLabel = `${formatDate(log.date)} for ${log.company}`;

          return (
            <tr key={log.id}>
              <RecordCell label="Date">{formatDate(log.date)}</RecordCell>
              <RecordCell label="Company">{log.company}</RecordCell>
              <RecordCell label="Manpower">{log.manpower}</RecordCell>
              <RecordCell label="Notes">{log.notes}</RecordCell>
              <RecordCell label="Actions" className="record-actions">
                <Button
                  size="sm"
                  aria-expanded={isExpanded}
                  aria-controls={detailId}
                  aria-label={`${
                    isExpanded ? "Close attachments" : "Attachments"
                  } for daily log ${logLabel}`}
                  onClick={() =>
                    setAttachmentLogId(isExpanded ? null : log.id)
                  }
                >
                  <Icon name="file-text" size={15} />
                  {isExpanded ? "Close" : "Attachments"}
                </Button>
                <Button
                  size="sm"
                  aria-expanded={relationshipLog?.id === log.id}
                  aria-controls={`daily-log-relationships-${log.id}`}
                  aria-label={`${
                    relationshipLog?.id === log.id
                      ? "Close relationships"
                      : "Relationships"
                  } for daily log ${logLabel}`}
                  onClick={() =>
                    setRelationshipLogId(
                      relationshipLog?.id === log.id ? null : log.id
                    )
                  }
                >
                  <Icon name="link" size={15} />
                  {relationshipLog?.id === log.id
                    ? "Close"
                    : "Relationships"}
                </Button>
              </RecordCell>
            </tr>
          );
        })}
      </RecordTable>

      {selectedLog && (
        <div
          id={`daily-log-attachments-${selectedLog.id}`}
          className="daily-log-attachment-detail"
          role="region"
          aria-label={`Attachments for daily log ${formatDate(
            selectedLog.date
          )} for ${selectedLog.company}`}
        >
          <AttachmentPanel
            projectId={projectId}
            parentType="daily_log"
            parentId={selectedLog.id}
            title="Daily Log Attachments"
            canUpload
            canDelete
            onError={onAttachmentError}
          />
        </div>
      )}
      {relationshipLog && (
        <div
          id={`daily-log-relationships-${relationshipLog.id}`}
          className="record-relationship-detail"
          role="region"
          aria-label={`Relationships for daily log ${formatDate(
            relationshipLog.date
          )} for ${relationshipLog.company}`}
        >
          <RelationshipPanel
            projectId={projectId}
            entityType="daily_log"
            entityId={relationshipLog.id}
            title="Daily Log Relationships"
            onNavigate={onNavigate}
            onError={onAttachmentError}
          />
        </div>
      )}
    </ProjectLayout>
  );
}

export default DailyLogsPage;
