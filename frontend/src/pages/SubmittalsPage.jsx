import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import { isSubmittalOverdue } from "../utils/submittal";

const STATUS_OPTIONS = [
  "Draft",
  "Submitted",
  "Under Review",
  "Approved",
  "Revise and Resubmit",
  "Rejected",
];

function SubmittalsPage({
  projectName,
  submittals,
  projectCompanies,
  editingSubmittalId,
  editingSubmittalNumber,
  specificationSection,
  title,
  responsibleCompany,
  submittedDate,
  requiredByDate,
  reviewedDate,
  status,
  reviewer,
  remarks,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onSave,
  onEdit,
  onCancelEdit,
  onDelete,
  onSpecificationSectionChange,
  onTitleChange,
  onResponsibleCompanyChange,
  onSubmittedDateChange,
  onRequiredByDateChange,
  onReviewedDateChange,
  onStatusChange,
  onReviewerChange,
  onRemarksChange,
  isSaving = false,
  isRefreshing = false,
  isLoading = false,
}) {
  const isEditing = editingSubmittalId !== null;

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="submittals"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Submittals"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            <Icon name="refresh" size={17} />
            {isRefreshing ? "Refreshing Submittals..." : "Refresh Submittals"}
          </Button>
        }
      />

      <Card
        as="form"
        title={
          isEditing
            ? `Edit ${editingSubmittalNumber}`
            : "Create Submittal"
        }
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <FormField
          label="Specification section"
          htmlFor="submittal-specification-section"
          required
        >
          <input
            id="submittal-specification-section"
            className="field-control"
            required
            value={specificationSection}
            onChange={(event) =>
              onSpecificationSectionChange(event.target.value)
            }
          />
        </FormField>

        <FormField label="Title" htmlFor="submittal-title" required>
          <input
            id="submittal-title"
            className="field-control"
            required
            value={title}
            onChange={(event) => onTitleChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Responsible company"
          htmlFor="submittal-responsible-company"
        >
          <input
            id="submittal-responsible-company"
            className="field-control"
            list="submittal-company-options"
            value={responsibleCompany}
            onChange={(event) =>
              onResponsibleCompanyChange(event.target.value)
            }
          />
          <datalist id="submittal-company-options">
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name} />
            ))}
          </datalist>
        </FormField>

        <FormField
          label="Submitted date"
          htmlFor="submittal-submitted-date"
        >
          <input
            id="submittal-submitted-date"
            className="field-control"
            type="date"
            value={submittedDate}
            onChange={(event) => onSubmittedDateChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Required-by date"
          htmlFor="submittal-required-by-date"
        >
          <input
            id="submittal-required-by-date"
            className="field-control"
            type="date"
            min={submittedDate || undefined}
            value={requiredByDate}
            onChange={(event) => onRequiredByDateChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Reviewed date"
          htmlFor="submittal-reviewed-date"
        >
          <input
            id="submittal-reviewed-date"
            className="field-control"
            type="date"
            min={submittedDate || undefined}
            value={reviewedDate}
            onChange={(event) => onReviewedDateChange(event.target.value)}
          />
        </FormField>

        <FormField label="Status" htmlFor="submittal-status">
          <select
            id="submittal-status"
            className="field-control"
            value={status}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Reviewer" htmlFor="submittal-reviewer">
          <input
            id="submittal-reviewer"
            className="field-control"
            value={reviewer}
            onChange={(event) => onReviewerChange(event.target.value)}
          />
        </FormField>

        <FormField label="Remarks" htmlFor="submittal-remarks">
          <textarea
            id="submittal-remarks"
            className="field-control"
            value={remarks}
            onChange={(event) => onRemarksChange(event.target.value)}
          />
        </FormField>

        <div className="submittal-form-actions">
          <Button
            type="submit"
            variant="primary"
            disabled={isSaving}
            aria-busy={isSaving}
          >
            {isSaving
              ? "Saving Submittal..."
              : isEditing
                ? "Update Submittal"
                : "Create Submittal"}
          </Button>
          {isEditing && (
            <Button onClick={onCancelEdit} disabled={isSaving}>
              Cancel Edit
            </Button>
          )}
        </div>
      </Card>

      <RecordTable
        label="Project submittals"
        isLoading={isLoading}
        loadingMessage="Loading Submittals..."
        emptyMessage="No submittals yet. Create the first submittal above."
        headers={[
          "Submittal Number",
          "Specification Section",
          "Title",
          "Responsible Company",
          "Submitted",
          "Required By",
          "Reviewed",
          "Status",
          "Reviewer",
          "Remarks",
          "Actions",
        ]}
      >
        {submittals.map((submittal) => {
          const isOverdue = isSubmittalOverdue(submittal);

          return (
            <tr key={submittal.id}>
              <RecordCell label="Submittal Number">
                {submittal.number}
              </RecordCell>
              <RecordCell label="Specification Section">
                {submittal.specification_section}
              </RecordCell>
              <RecordCell label="Title">{submittal.title}</RecordCell>
              <RecordCell label="Responsible Company">
                {submittal.responsible_company || "-"}
              </RecordCell>
              <RecordCell label="Submitted">
                {formatDate(submittal.submitted_date)}
              </RecordCell>
              <RecordCell label="Required By">
                {formatDate(submittal.required_by_date)}
              </RecordCell>
              <RecordCell label="Reviewed">
                {formatDate(submittal.reviewed_date)}
              </RecordCell>
              <RecordCell label="Status">
                <span className="submittal-status">
                  <StatusBadge value={submittal.status} />
                  {isOverdue && (
                    <span className="submittal-overdue">Overdue</span>
                  )}
                </span>
              </RecordCell>
              <RecordCell label="Reviewer">
                {submittal.reviewer || "-"}
              </RecordCell>
              <RecordCell
                label="Remarks"
                className="submittal-remarks-summary"
              >
                {submittal.remarks || "No remarks"}
              </RecordCell>
              <RecordCell label="Actions" className="record-actions">
                <Button
                  onClick={() => onEdit(submittal)}
                  aria-label={`Edit ${submittal.number}`}
                >
                  <Icon name="pencil" size={16} />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    onDelete(submittal.id, submittal.number)
                  }
                  aria-label={`Delete ${submittal.number}`}
                >
                  <Icon name="trash" size={16} />
                  Delete
                </Button>
              </RecordCell>
            </tr>
          );
        })}
      </RecordTable>
    </ProjectLayout>
  );
}

export default SubmittalsPage;
