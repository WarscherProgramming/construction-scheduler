import { useMemo, useState } from "react";

import AttachmentPanel from "../components/AttachmentPanel";
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
import {
  CHANGE_ORDER_STATUSES,
  formatCurrency,
  formatScheduleImpact,
} from "../utils/changeOrder";

function CompanyOptions({ companies }) {
  return companies.map((company) => (
    <option key={company.id} value={company.name} />
  ));
}

function DetailList({ children }) {
  return <dl className="change-order-detail-list">{children}</dl>;
}

function Detail({ label, children }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function ChangeOrdersPage({
  projectId,
  projectName,
  changeOrders,
  projectCompanies,
  editingChangeOrderId,
  editingChangeOrderNumber,
  changeOrderDate,
  changeOrderTitle,
  changeOrderCompany,
  changeOrderStatus,
  changeOrderDescription,
  changeOrderReason,
  changeOrderProposedAmount,
  changeOrderApprovedAmount,
  changeOrderScheduleImpactDays,
  changeOrderRequestedDate,
  changeOrderSubmittedDate,
  changeOrderApprovedDate,
  changeOrderExecutedDate,
  changeOrderResponsibleParty,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onSave,
  onEdit,
  onCancelEdit,
  onDelete,
  onDateChange,
  onTitleChange,
  onCompanyChange,
  onStatusChange,
  onDescriptionChange,
  onReasonChange,
  onProposedAmountChange,
  onApprovedAmountChange,
  onScheduleImpactDaysChange,
  onRequestedDateChange,
  onSubmittedDateChange,
  onApprovedDateChange,
  onExecutedDateChange,
  onResponsiblePartyChange,
  onAttachmentError,
  isSaving = false,
  isRefreshing = false,
  isLoading = false,
  isLoadingCompanies = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [attachmentChangeOrderId, setAttachmentChangeOrderId] =
    useState(null);
  const isEditing = editingChangeOrderId !== null;
  const hasKnownStatus = CHANGE_ORDER_STATUSES.includes(changeOrderStatus);

  const companyFilterOptions = useMemo(
    () =>
      Array.from(
        new Set(
          [
            ...projectCompanies.map((company) => company.name),
            ...changeOrders.map((changeOrder) => changeOrder.company),
          ].filter(Boolean)
        )
      ).sort(),
    [changeOrders, projectCompanies]
  );

  const filteredChangeOrders = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return changeOrders.filter((changeOrder) => {
      const matchesStatus =
        !statusFilter || changeOrder.status === statusFilter;
      const matchesCompany =
        !companyFilter || changeOrder.company === companyFilter;
      const matchesQuery =
        !query ||
        [
          changeOrder.co_number,
          changeOrder.title,
          changeOrder.company,
          changeOrder.status,
          changeOrder.description,
          changeOrder.reason,
          changeOrder.responsible_party,
          changeOrder.amount,
          changeOrder.proposed_amount,
          changeOrder.approved_amount,
        ].some((value) =>
          String(value || "").toLowerCase().includes(query)
        );

      return matchesStatus && matchesCompany && matchesQuery;
    });
  }, [changeOrders, companyFilter, searchQuery, statusFilter]);
  const selectedChangeOrder = filteredChangeOrders.find(
    (changeOrder) => changeOrder.id === attachmentChangeOrderId
  );

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="changeOrders"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title="Change Orders"
        actions={
          <Button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-busy={isRefreshing}
          >
            <Icon name="refresh" size={17} />
            {isRefreshing
              ? "Refreshing change orders..."
              : "Refresh Change Orders"}
          </Button>
        }
      />

      <Card
        as="form"
        title={
          isEditing
            ? `Edit ${editingChangeOrderNumber}`
            : "Create Change Order"
        }
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <FormField
          label="Change order number"
          htmlFor="change-order-number"
        >
          <input
            id="change-order-number"
            className="field-control"
            readOnly
            value={
              isEditing
                ? editingChangeOrderNumber
                : "Assigned when saved"
            }
          />
        </FormField>

        <FormField label="Record date" htmlFor="change-order-date" required>
          <input
            id="change-order-date"
            className="field-control"
            type="date"
            required
            value={changeOrderDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>

        <FormField
          label="Title"
          htmlFor="change-order-title"
          hint="A title or description is required."
        >
          <input
            id="change-order-title"
            className="field-control"
            maxLength={500}
            value={changeOrderTitle}
            onChange={(event) => onTitleChange(event.target.value)}
          />
        </FormField>

        <FormField label="Company" htmlFor="change-order-company">
          <input
            id="change-order-company"
            className="field-control"
            list="change-order-company-options"
            disabled={isLoadingCompanies}
            value={changeOrderCompany}
            onChange={(event) => onCompanyChange(event.target.value)}
          />
          <datalist id="change-order-company-options">
            <CompanyOptions companies={projectCompanies} />
          </datalist>
        </FormField>

        <FormField label="Status" htmlFor="change-order-status">
          <select
            id="change-order-status"
            className="field-control"
            value={changeOrderStatus}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            {!hasKnownStatus && (
              <option value={changeOrderStatus}>
                {changeOrderStatus || "Unknown"}
              </option>
            )}
            {CHANGE_ORDER_STATUSES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Proposed amount"
          htmlFor="change-order-proposed-amount"
          hint="U.S. dollars, with up to two decimal places."
        >
          <input
            id="change-order-proposed-amount"
            className="field-control"
            inputMode="decimal"
            placeholder="0.00"
            value={changeOrderProposedAmount}
            onChange={(event) =>
              onProposedAmountChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Approved amount"
          htmlFor="change-order-approved-amount"
          hint="U.S. dollars, with up to two decimal places."
        >
          <input
            id="change-order-approved-amount"
            className="field-control"
            inputMode="decimal"
            placeholder="0.00"
            value={changeOrderApprovedAmount}
            onChange={(event) =>
              onApprovedAmountChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Schedule impact"
          htmlFor="change-order-schedule-impact"
          hint="Whole days; negative values reduce the schedule."
        >
          <input
            id="change-order-schedule-impact"
            className="field-control"
            type="number"
            step="1"
            value={changeOrderScheduleImpactDays}
            onChange={(event) =>
              onScheduleImpactDaysChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Requested date"
          htmlFor="change-order-requested-date"
        >
          <input
            id="change-order-requested-date"
            className="field-control"
            type="date"
            value={changeOrderRequestedDate}
            onChange={(event) =>
              onRequestedDateChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Submitted date"
          htmlFor="change-order-submitted-date"
        >
          <input
            id="change-order-submitted-date"
            className="field-control"
            type="date"
            min={changeOrderRequestedDate || undefined}
            value={changeOrderSubmittedDate}
            onChange={(event) =>
              onSubmittedDateChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Approved date"
          htmlFor="change-order-approved-date"
        >
          <input
            id="change-order-approved-date"
            className="field-control"
            type="date"
            min={changeOrderSubmittedDate || undefined}
            value={changeOrderApprovedDate}
            onChange={(event) =>
              onApprovedDateChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Executed date"
          htmlFor="change-order-executed-date"
        >
          <input
            id="change-order-executed-date"
            className="field-control"
            type="date"
            min={changeOrderApprovedDate || undefined}
            value={changeOrderExecutedDate}
            onChange={(event) =>
              onExecutedDateChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Responsible party"
          htmlFor="change-order-responsible-party"
        >
          <input
            id="change-order-responsible-party"
            className="field-control"
            list="change-order-company-options"
            disabled={isLoadingCompanies}
            value={changeOrderResponsibleParty}
            onChange={(event) =>
              onResponsiblePartyChange(event.target.value)
            }
          />
        </FormField>

        <FormField
          label="Description"
          htmlFor="change-order-description"
          hint="A title or description is required."
        >
          <textarea
            id="change-order-description"
            className="field-control"
            value={changeOrderDescription}
            onChange={(event) => onDescriptionChange(event.target.value)}
          />
        </FormField>

        <FormField label="Reason" htmlFor="change-order-reason">
          <textarea
            id="change-order-reason"
            className="field-control"
            value={changeOrderReason}
            onChange={(event) => onReasonChange(event.target.value)}
          />
        </FormField>

        <div className="change-order-form-actions">
          <Button
            type="submit"
            variant="primary"
            disabled={isSaving}
            aria-busy={isSaving}
          >
            {isSaving
              ? "Saving change order..."
              : isEditing
                ? "Update Change Order"
                : "Create Change Order"}
          </Button>
          {isEditing && (
            <Button onClick={onCancelEdit} disabled={isSaving}>
              Cancel Edit
            </Button>
          )}
        </div>
      </Card>

      <RecordFilters resultCount={filteredChangeOrders.length}>
        <FormField label="Search" htmlFor="change-order-search">
          <input
            id="change-order-search"
            className="field-control"
            type="search"
            placeholder="Number, title, company, amount, or description"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </FormField>
        <FormField label="Status" htmlFor="change-order-status-filter">
          <select
            id="change-order-status-filter"
            className="field-control"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            {CHANGE_ORDER_STATUSES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Company" htmlFor="change-order-company-filter">
          <select
            id="change-order-company-filter"
            className="field-control"
            value={companyFilter}
            disabled={isLoadingCompanies}
            onChange={(event) => setCompanyFilter(event.target.value)}
          >
            <option value="">All companies</option>
            {companyFilterOptions.map((company) => (
              <option key={company} value={company}>
                {company}
              </option>
            ))}
          </select>
        </FormField>
      </RecordFilters>

      <RecordTable
        label="Change orders"
        isLoading={isLoading}
        loadingMessage="Loading change orders..."
        emptyMessage={
          changeOrders.length
            ? "No change orders match the current filters."
            : "No change orders yet. Create the first change order above."
        }
        headers={[
          "Number",
          "Title",
          "Company",
          "Status",
          "Amounts",
          "Schedule Impact",
          "Lifecycle",
          "Responsible Party",
          "Details",
          "Actions",
        ]}
      >
        {filteredChangeOrders.map((changeOrder) => {
          const hasEnhancedAmount =
            changeOrder.proposed_amount != null ||
            changeOrder.approved_amount != null;

          return (
            <tr key={changeOrder.id}>
              <RecordCell label="Number">
                {changeOrder.co_number}
              </RecordCell>
              <RecordCell label="Title">
                {changeOrder.title || "Untitled change order"}
              </RecordCell>
              <RecordCell label="Company">
                {changeOrder.company || "Not specified"}
              </RecordCell>
              <RecordCell label="Status">
                <StatusBadge value={changeOrder.status} />
              </RecordCell>
              <RecordCell label="Amounts">
                <DetailList>
                  <Detail label="Proposed">
                    {formatCurrency(changeOrder.proposed_amount)}
                  </Detail>
                  <Detail label="Approved">
                    {formatCurrency(changeOrder.approved_amount)}
                  </Detail>
                  {!hasEnhancedAmount && changeOrder.amount && (
                    <Detail label="Legacy amount">
                      {changeOrder.amount}
                    </Detail>
                  )}
                </DetailList>
              </RecordCell>
              <RecordCell label="Schedule Impact">
                {formatScheduleImpact(changeOrder.schedule_impact_days)}
              </RecordCell>
              <RecordCell label="Lifecycle">
                <DetailList>
                  <Detail label="Record">
                    {formatDate(changeOrder.date)}
                  </Detail>
                  <Detail label="Requested">
                    {formatDate(changeOrder.requested_date)}
                  </Detail>
                  <Detail label="Submitted">
                    {formatDate(changeOrder.submitted_date)}
                  </Detail>
                  <Detail label="Approved">
                    {formatDate(changeOrder.approved_date)}
                  </Detail>
                  <Detail label="Executed">
                    {formatDate(changeOrder.executed_date)}
                  </Detail>
                </DetailList>
              </RecordCell>
              <RecordCell label="Responsible Party">
                {changeOrder.responsible_party || "Not specified"}
              </RecordCell>
              <RecordCell label="Details">
                <DetailList>
                  <Detail label="Description">
                    {changeOrder.description || "No description"}
                  </Detail>
                  <Detail label="Reason">
                    {changeOrder.reason || "No reason"}
                  </Detail>
                </DetailList>
              </RecordCell>
              <RecordCell label="Actions" className="record-actions">
                <Button
                  aria-expanded={
                    selectedChangeOrder?.id === changeOrder.id
                  }
                  aria-controls={`change-order-attachments-${changeOrder.id}`}
                  aria-label={`${
                    selectedChangeOrder?.id === changeOrder.id
                      ? "Close attachments"
                      : "Attachments"
                  } for change order ${changeOrder.co_number}`}
                  onClick={() =>
                    setAttachmentChangeOrderId(
                      selectedChangeOrder?.id === changeOrder.id
                        ? null
                        : changeOrder.id
                    )
                  }
                >
                  <Icon name="file-text" size={16} />
                  {selectedChangeOrder?.id === changeOrder.id
                    ? "Close"
                    : "Attachments"}
                </Button>
                <Button
                  onClick={() => onEdit(changeOrder)}
                  aria-label={`Edit change order ${changeOrder.co_number}`}
                >
                  <Icon name="pencil" size={16} />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    onDelete(changeOrder.id, changeOrder.co_number)
                  }
                  aria-label={`Delete change order ${changeOrder.co_number}`}
                >
                  <Icon name="trash" size={16} />
                  Delete
                </Button>
              </RecordCell>
            </tr>
          );
        })}
      </RecordTable>

      {selectedChangeOrder && (
        <div
          id={`change-order-attachments-${selectedChangeOrder.id}`}
          className="record-attachment-detail"
          role="region"
          aria-label={`Attachments for change order ${selectedChangeOrder.co_number}`}
        >
          <AttachmentPanel
            projectId={projectId}
            parentType="change_order"
            parentId={selectedChangeOrder.id}
            title="Change Order Attachments"
            canUpload
            canDelete
            onError={onAttachmentError}
          />
        </div>
      )}
    </ProjectLayout>
  );
}

export default ChangeOrdersPage;
