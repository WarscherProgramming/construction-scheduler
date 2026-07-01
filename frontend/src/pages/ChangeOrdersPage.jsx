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

function CompanyOptions({ companies }) {
  return companies.map((company) => (
    <option key={company.id} value={company.name}>
      {company.name}
    </option>
  ));
}

function ChangeOrdersPage({
  projectName,
  changeOrders,
  projectCompanies,
  changeOrderDate,
  changeOrderNumber,
  changeOrderCompany,
  changeOrderStatus,
  changeOrderDescription,
  changeOrderAmount,
  changeOrderResponsibleParty,
  formatDate,
  onNavigate,
  onLogout,
  onRefresh,
  onCreate,
  onDelete,
  onDateChange,
  onNumberChange,
  onCompanyChange,
  onStatusChange,
  onDescriptionChange,
  onAmountChange,
  onResponsiblePartyChange,
  isCreating = false,
  isRefreshing = false,
  isLoading = false,
  isLoadingCompanies = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");

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
          changeOrder.company,
          changeOrder.description,
          changeOrder.responsible_party,
          changeOrder.amount,
        ].some((value) => String(value || "").toLowerCase().includes(query));

      return matchesStatus && matchesCompany && matchesQuery;
    });
  }, [changeOrders, companyFilter, searchQuery, statusFilter]);

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
              ? "Refreshing change orders…"
              : "Refresh Change Orders"}
          </Button>
        }
      />

      <Card
        as="form"
        title="Create Change Order"
        bodyClassName="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <FormField label="Date" htmlFor="change-order-date" required>
          <input
            id="change-order-date"
            className="field-control"
            type="date"
            required
            value={changeOrderDate}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </FormField>
        <FormField label="Change order number" htmlFor="change-order-number" required>
          <input
            id="change-order-number"
            className="field-control"
            required
            value={changeOrderNumber}
            onChange={(event) => onNumberChange(event.target.value)}
          />
        </FormField>
        <FormField label="Company" htmlFor="change-order-company">
          <select
            id="change-order-company"
            className="field-control"
            value={changeOrderCompany}
            disabled={isLoadingCompanies}
            onChange={(event) => onCompanyChange(event.target.value)}
          >
            <option value="">
              {isLoadingCompanies ? "Loading companies…" : "Select company"}
            </option>
            <CompanyOptions companies={projectCompanies} />
          </select>
        </FormField>
        <FormField label="Status" htmlFor="change-order-status">
          <select
            id="change-order-status"
            className="field-control"
            value={changeOrderStatus}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
            <option value="Void">Void</option>
          </select>
        </FormField>
        <FormField label="Amount" htmlFor="change-order-amount">
          <input
            id="change-order-amount"
            className="field-control"
            inputMode="decimal"
            value={changeOrderAmount}
            onChange={(event) => onAmountChange(event.target.value)}
          />
        </FormField>
        <FormField
          label="Responsible party"
          htmlFor="change-order-responsible-party"
        >
          <select
            id="change-order-responsible-party"
            className="field-control"
            value={changeOrderResponsibleParty}
            disabled={isLoadingCompanies}
            onChange={(event) => onResponsiblePartyChange(event.target.value)}
          >
            <option value="">Select responsible party</option>
            <CompanyOptions companies={projectCompanies} />
          </select>
        </FormField>
        <FormField label="Description" htmlFor="change-order-description">
          <textarea
            id="change-order-description"
            className="field-control"
            value={changeOrderDescription}
            onChange={(event) => onDescriptionChange(event.target.value)}
          />
        </FormField>

        <Button
          type="submit"
          variant="primary"
          disabled={isCreating}
          aria-busy={isCreating}
        >
          {isCreating ? "Saving change order…" : "Save Change Order"}
        </Button>
      </Card>

      <RecordFilters resultCount={filteredChangeOrders.length}>
        <FormField label="Search" htmlFor="change-order-search">
          <input
            id="change-order-search"
            className="field-control"
            type="search"
            placeholder="Number, company, amount, or description"
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
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
            <option value="Void">Void</option>
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
            <CompanyOptions companies={projectCompanies} />
          </select>
        </FormField>
      </RecordFilters>

      <RecordTable
        label="Change orders"
        isLoading={isLoading}
        loadingMessage="Loading change orders…"
        emptyMessage={
          changeOrders.length
            ? "No change orders match the current filters."
            : "No change orders yet. Create the first change order above."
        }
        headers={[
          "Date",
          "CO Number",
          "Company",
          "Status",
          "Amount",
          "Responsible Party",
          "Description",
          "Actions",
        ]}
      >
        {filteredChangeOrders.map((changeOrder) => (
          <tr key={changeOrder.id}>
            <RecordCell label="Date">
              {formatDate(changeOrder.date)}
            </RecordCell>
            <RecordCell label="CO Number">
              {changeOrder.co_number}
            </RecordCell>
            <RecordCell label="Company">{changeOrder.company}</RecordCell>
            <RecordCell label="Status">
              <StatusBadge value={changeOrder.status} />
            </RecordCell>
            <RecordCell label="Amount">{changeOrder.amount}</RecordCell>
            <RecordCell label="Responsible Party">
              {changeOrder.responsible_party}
            </RecordCell>
            <RecordCell label="Description">
              {changeOrder.description}
            </RecordCell>
            <RecordCell label="Actions" className="record-actions">
              <Button
                variant="danger"
                onClick={() => onDelete(changeOrder.id)}
                aria-label={`Delete change order ${changeOrder.co_number}`}
              >
                <Icon name="trash" size={16} />
                Delete
              </Button>
            </RecordCell>
          </tr>
        ))}
      </RecordTable>
    </ProjectLayout>
  );
}

export default ChangeOrdersPage;
