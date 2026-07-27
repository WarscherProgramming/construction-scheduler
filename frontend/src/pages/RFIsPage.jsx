import { useState } from "react";

import AttachmentPanel from "../components/AttachmentPanel";
import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import { isPastLocalDate } from "../utils/date";

function RFIsPage({
  projectId,
  projectName,
  rfis,
  projectCompanies,
  editingRFIId,
  editingRFINumber,
  rfiSubject,
  rfiQuestion,
  rfiResponsibleCompany,
  rfiSubmittedDate,
  rfiDueDate,
  rfiResponse,
  rfiStatus,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onSave,
  onEdit,
  onCancelEdit,
  onDelete,
  onSubjectChange,
  onQuestionChange,
  onResponsibleCompanyChange,
  onSubmittedDateChange,
  onDueDateChange,
  onResponseChange,
  onStatusChange,
  onAttachmentError,
  isSaving = false,
  isRefreshing = false,
  isLoading = false,
}) {
  const isEditing = editingRFIId !== null;
  const [attachmentRFIId, setAttachmentRFIId] = useState(null);
  const selectedRFI = rfis.find((rfi) => rfi.id === attachmentRFIId);

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="rfis"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Requests for Information"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            <Icon name="refresh" size={17} />
            {isRefreshing ? "Refreshing RFIs..." : "Refresh RFIs"}
          </Button>
        }
      />

      <Card
        as="form"
        title={isEditing ? `Edit ${editingRFINumber}` : "Create RFI"}
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <FormField label="Subject" htmlFor="rfi-subject" required>
          <input
            id="rfi-subject"
            className="field-control"
            required
            value={rfiSubject}
            onChange={(event) => onSubjectChange(event.target.value)}
          />
        </FormField>

        <FormField label="Question" htmlFor="rfi-question" required>
          <textarea
            id="rfi-question"
            className="field-control"
            required
            value={rfiQuestion}
            onChange={(event) => onQuestionChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Responsible company"
          htmlFor="rfi-responsible-company"
        >
          <input
            id="rfi-responsible-company"
            className="field-control"
            list="rfi-company-options"
            value={rfiResponsibleCompany}
            onChange={(event) =>
              onResponsibleCompanyChange(event.target.value)
            }
          />
          <datalist id="rfi-company-options">
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name} />
            ))}
          </datalist>
        </FormField>

        <FormField
          label="Submitted date"
          htmlFor="rfi-submitted-date"
          required
        >
          <input
            id="rfi-submitted-date"
            className="field-control"
            type="date"
            required
            value={rfiSubmittedDate}
            onChange={(event) => onSubmittedDateChange(event.target.value)}
          />
        </FormField>

        <FormField label="Due date" htmlFor="rfi-due-date">
          <input
            id="rfi-due-date"
            className="field-control"
            type="date"
            min={rfiSubmittedDate || undefined}
            value={rfiDueDate}
            onChange={(event) => onDueDateChange(event.target.value)}
          />
        </FormField>

        <FormField label="Status" htmlFor="rfi-status">
          <select
            id="rfi-status"
            className="field-control"
            value={rfiStatus}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            <option value="Open">Open</option>
            <option value="Pending">Pending</option>
            <option value="Closed">Closed</option>
          </select>
        </FormField>

        <FormField label="Response" htmlFor="rfi-response">
          <textarea
            id="rfi-response"
            className="field-control"
            value={rfiResponse}
            onChange={(event) => onResponseChange(event.target.value)}
          />
        </FormField>

        <div className="rfi-form-actions">
          <Button
            type="submit"
            variant="primary"
            disabled={isSaving}
            aria-busy={isSaving}
          >
            {isSaving
              ? "Saving RFI..."
              : isEditing
                ? "Update RFI"
                : "Create RFI"}
          </Button>
          {isEditing && (
            <Button onClick={onCancelEdit} disabled={isSaving}>
              Cancel Edit
            </Button>
          )}
        </div>
      </Card>

      <RecordTable
        label="Requests for information"
        isLoading={isLoading}
        loadingMessage="Loading RFIs..."
        emptyMessage="No RFIs yet. Create the first RFI above."
        headers={[
          "RFI Number",
          "Subject",
          "Responsible Company",
          "Submitted",
          "Due",
          "Status",
          "Response",
          "Actions",
        ]}
      >
        {rfis.map((rfi) => {
          const isOverdue =
            rfi.status !== "Closed" && isPastLocalDate(rfi.due_date);
          const responseSummary =
            rfi.response ||
            (rfi.status === "Closed"
              ? "Closed without a response"
              : "Awaiting response");

          return (
            <tr key={rfi.id}>
              <RecordCell label="RFI Number">{rfi.number}</RecordCell>
              <RecordCell label="Subject">{rfi.subject}</RecordCell>
              <RecordCell label="Responsible Company">
                {rfi.responsible_company || "-"}
              </RecordCell>
              <RecordCell label="Submitted">
                {formatDate(rfi.submitted_date)}
              </RecordCell>
              <RecordCell label="Due">{formatDate(rfi.due_date)}</RecordCell>
              <RecordCell label="Status">
                <span className="rfi-status">
                  <StatusBadge value={rfi.status} />
                  {isOverdue && (
                    <span className="rfi-overdue">Overdue</span>
                  )}
                </span>
              </RecordCell>
              <RecordCell
                label="Response"
                className="rfi-response-summary"
              >
                {responseSummary}
              </RecordCell>
              <RecordCell label="Actions" className="record-actions">
                <Button
                  aria-expanded={selectedRFI?.id === rfi.id}
                  aria-controls={`rfi-attachments-${rfi.id}`}
                  aria-label={`${
                    selectedRFI?.id === rfi.id
                      ? "Close attachments"
                      : "Attachments"
                  } for RFI ${rfi.number}`}
                  onClick={() =>
                    setAttachmentRFIId(
                      selectedRFI?.id === rfi.id ? null : rfi.id
                    )
                  }
                >
                  <Icon name="file-text" size={16} />
                  {selectedRFI?.id === rfi.id ? "Close" : "Attachments"}
                </Button>
                <Button
                  onClick={() => onEdit(rfi)}
                  aria-label={`Edit ${rfi.number}`}
                >
                  <Icon name="pencil" size={16} />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  onClick={() => onDelete(rfi.id, rfi.number)}
                  aria-label={`Delete ${rfi.number}`}
                >
                  <Icon name="trash" size={16} />
                  Delete
                </Button>
              </RecordCell>
            </tr>
          );
        })}
      </RecordTable>

      {selectedRFI && (
        <div
          id={`rfi-attachments-${selectedRFI.id}`}
          className="record-attachment-detail"
          role="region"
          aria-label={`Attachments for RFI ${selectedRFI.number}`}
        >
          <AttachmentPanel
            projectId={projectId}
            parentType="rfi"
            parentId={selectedRFI.id}
            title="RFI Attachments"
            canUpload
            canDelete
            onError={onAttachmentError}
          />
        </div>
      )}
    </ProjectLayout>
  );
}

export default RFIsPage;
