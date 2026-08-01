import { useState } from "react";

import AttachmentPanel from "../components/AttachmentPanel";
import FormField from "../components/FormField";
import RecordCell from "../components/RecordCell";
import RecordTable from "../components/RecordTable";
import RelationshipPanel from "../components/relationships/RelationshipPanel";
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import { isPunchItemOverdue } from "../utils/punchItem";

const PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical"];
const STATUS_OPTIONS = ["Open", "In Progress", "Completed", "Verified"];

function PunchItemsPage({
  projectId,
  projectName,
  punchItems,
  projectCompanies,
  editingPunchItemId,
  editingPunchItemNumber,
  location,
  trade,
  description,
  responsibleCompany,
  assignedTo,
  priority,
  status,
  dueDate,
  completedDate,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onSave,
  onEdit,
  onCancelEdit,
  onDelete,
  onLocationChange,
  onTradeChange,
  onDescriptionChange,
  onResponsibleCompanyChange,
  onAssignedToChange,
  onPriorityChange,
  onStatusChange,
  onDueDateChange,
  onCompletedDateChange,
  onAttachmentError,
  isSaving = false,
  isRefreshing = false,
  isLoading = false,
}) {
  const isEditing = editingPunchItemId !== null;
  const [attachmentPunchItemId, setAttachmentPunchItemId] = useState(null);
  const [relationshipPunchItemId, setRelationshipPunchItemId] =
    useState(null);
  const selectedPunchItem = punchItems.find(
    (punchItem) => punchItem.id === attachmentPunchItemId
  );
  const relationshipPunchItem = punchItems.find(
    (punchItem) => punchItem.id === relationshipPunchItemId
  );

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="punchItems"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Punch List"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            <Icon name="refresh" size={17} />
            {isRefreshing
              ? "Refreshing Punch Items..."
              : "Refresh Punch Items"}
          </Button>
        }
      />

      <Card
        as="form"
        title={
          isEditing
            ? `Edit ${editingPunchItemNumber}`
            : "Create Punch Item"
        }
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <FormField label="Location" htmlFor="punch-item-location" required>
          <input
            id="punch-item-location"
            className="field-control"
            required
            value={location}
            onChange={(event) => onLocationChange(event.target.value)}
          />
        </FormField>

        <FormField label="Trade" htmlFor="punch-item-trade">
          <input
            id="punch-item-trade"
            className="field-control"
            value={trade}
            onChange={(event) => onTradeChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Description"
          htmlFor="punch-item-description"
          required
        >
          <textarea
            id="punch-item-description"
            className="field-control"
            required
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Responsible company"
          htmlFor="punch-item-responsible-company"
        >
          <input
            id="punch-item-responsible-company"
            className="field-control"
            list="punch-item-company-options"
            value={responsibleCompany}
            onChange={(event) =>
              onResponsibleCompanyChange(event.target.value)
            }
          />
          <datalist id="punch-item-company-options">
            {projectCompanies.map((company) => (
              <option key={company.id} value={company.name} />
            ))}
          </datalist>
        </FormField>

        <FormField label="Assigned to" htmlFor="punch-item-assigned-to">
          <input
            id="punch-item-assigned-to"
            className="field-control"
            value={assignedTo}
            onChange={(event) => onAssignedToChange(event.target.value)}
          />
        </FormField>

        <FormField label="Priority" htmlFor="punch-item-priority">
          <select
            id="punch-item-priority"
            className="field-control"
            value={priority}
            onChange={(event) => onPriorityChange(event.target.value)}
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Status" htmlFor="punch-item-status">
          <select
            id="punch-item-status"
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

        <FormField label="Due date" htmlFor="punch-item-due-date">
          <input
            id="punch-item-due-date"
            className="field-control"
            type="date"
            value={dueDate}
            onChange={(event) => onDueDateChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Completed date"
          htmlFor="punch-item-completed-date"
        >
          <input
            id="punch-item-completed-date"
            className="field-control"
            type="date"
            min={dueDate || undefined}
            value={completedDate}
            onChange={(event) => onCompletedDateChange(event.target.value)}
          />
        </FormField>

        <div className="punch-item-form-actions">
          <Button
            type="submit"
            variant="primary"
            disabled={isSaving}
            aria-busy={isSaving}
          >
            {isSaving
              ? "Saving Punch Item..."
              : isEditing
                ? "Update Punch Item"
                : "Create Punch Item"}
          </Button>
          {isEditing && (
            <Button onClick={onCancelEdit} disabled={isSaving}>
              Cancel Edit
            </Button>
          )}
        </div>
      </Card>

      <RecordTable
        label="Project punch items"
        isLoading={isLoading}
        loadingMessage="Loading Punch Items..."
        emptyMessage="No punch items yet. Create the first punch item above."
        headers={[
          "Punch Number",
          "Location",
          "Trade",
          "Description",
          "Responsible Company",
          "Assigned To",
          "Priority",
          "Status",
          "Due Date",
          "Completed Date",
          "Actions",
        ]}
      >
        {punchItems.map((punchItem) => {
          const isOverdue = isPunchItemOverdue(punchItem);

          return (
            <tr key={punchItem.id}>
              <RecordCell label="Punch Number">
                {punchItem.number}
              </RecordCell>
              <RecordCell label="Location">{punchItem.location}</RecordCell>
              <RecordCell label="Trade">{punchItem.trade || "-"}</RecordCell>
              <RecordCell
                label="Description"
                className="punch-item-description-summary"
              >
                {punchItem.description}
              </RecordCell>
              <RecordCell label="Responsible Company">
                {punchItem.responsible_company || "-"}
              </RecordCell>
              <RecordCell label="Assigned To">
                {punchItem.assigned_to || "-"}
              </RecordCell>
              <RecordCell label="Priority">
                <StatusBadge value={punchItem.priority} />
              </RecordCell>
              <RecordCell label="Status">
                <span className="punch-item-status">
                  <StatusBadge value={punchItem.status} />
                  {isOverdue && (
                    <span className="punch-item-overdue">Overdue</span>
                  )}
                </span>
              </RecordCell>
              <RecordCell label="Due Date">
                {formatDate(punchItem.due_date)}
              </RecordCell>
              <RecordCell label="Completed Date">
                {formatDate(punchItem.completed_date)}
              </RecordCell>
              <RecordCell label="Actions" className="record-actions">
                <Button
                  aria-expanded={selectedPunchItem?.id === punchItem.id}
                  aria-controls={`punch-item-attachments-${punchItem.id}`}
                  aria-label={`${
                    selectedPunchItem?.id === punchItem.id
                      ? "Close attachments"
                      : "Attachments"
                  } for Punch Item ${punchItem.number}`}
                  onClick={() =>
                    setAttachmentPunchItemId(
                      selectedPunchItem?.id === punchItem.id
                        ? null
                        : punchItem.id
                    )
                  }
                >
                  <Icon name="file-text" size={16} />
                  {selectedPunchItem?.id === punchItem.id
                    ? "Close"
                    : "Attachments"}
                </Button>
                <Button
                  aria-expanded={
                    relationshipPunchItem?.id === punchItem.id
                  }
                  aria-controls={`punch-item-relationships-${punchItem.id}`}
                  aria-label={`${
                    relationshipPunchItem?.id === punchItem.id
                      ? "Close relationships"
                      : "Relationships"
                  } for Punch Item ${punchItem.number}`}
                  onClick={() =>
                    setRelationshipPunchItemId(
                      relationshipPunchItem?.id === punchItem.id
                        ? null
                        : punchItem.id
                    )
                  }
                >
                  <Icon name="link" size={16} />
                  {relationshipPunchItem?.id === punchItem.id
                    ? "Close"
                    : "Relationships"}
                </Button>
                <Button
                  onClick={() => onEdit(punchItem)}
                  aria-label={`Edit ${punchItem.number}`}
                >
                  <Icon name="pencil" size={16} />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    onDelete(punchItem.id, punchItem.number)
                  }
                  aria-label={`Delete ${punchItem.number}`}
                >
                  <Icon name="trash" size={16} />
                  Delete
                </Button>
              </RecordCell>
            </tr>
          );
        })}
      </RecordTable>

      {selectedPunchItem && (
        <div
          id={`punch-item-attachments-${selectedPunchItem.id}`}
          className="record-attachment-detail"
          role="region"
          aria-label={`Attachments for Punch Item ${selectedPunchItem.number}`}
        >
          <AttachmentPanel
            projectId={projectId}
            parentType="punch_item"
            parentId={selectedPunchItem.id}
            title="Punch Item Attachments"
            canUpload
            canDelete
            onError={onAttachmentError}
          />
        </div>
      )}
      {relationshipPunchItem && (
        <div
          id={`punch-item-relationships-${relationshipPunchItem.id}`}
          className="record-relationship-detail"
          role="region"
          aria-label={`Relationships for Punch Item ${relationshipPunchItem.number}`}
        >
          <RelationshipPanel
            projectId={projectId}
            entityType="punch_item"
            entityId={relationshipPunchItem.id}
            title="Punch Item Relationships"
            onNavigate={onNavigate}
            onError={onAttachmentError}
          />
        </div>
      )}
    </ProjectLayout>
  );
}

export default PunchItemsPage;
