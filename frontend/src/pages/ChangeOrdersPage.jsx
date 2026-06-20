import { useMemo, useState } from "react";

import FormField from "../components/FormField";
import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordFilters from "../components/RecordFilters";
import RecordTable from "../components/RecordTable";
import StatusBadge from "../components/StatusBadge";
import { buttonStyle, tableCellStyle } from "../styles";

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
  onBack,
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
    <ProjectPageLayout title={`${projectName} Change Orders`} onBack={onBack}>
      <form
        className="form-stack form-card"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate();
        }}
      >
        <h3>Create Change Order</h3>

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
            onChange={(event) => onCompanyChange(event.target.value)}
          >
            <option value="">Select company</option>
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

        <button
          type="submit"
          className="button-primary"
          disabled={isCreating}
          aria-busy={isCreating}
          style={buttonStyle}
        >
          {isCreating ? "Saving change order…" : "Save Change Order"}
        </button>
      </form>

      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-busy={isRefreshing}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        {isRefreshing
          ? "Refreshing change orders…"
          : "Refresh Change Orders"}
      </button>

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
            onChange={(event) => setCompanyFilter(event.target.value)}
          >
            <option value="">All companies</option>
            <CompanyOptions companies={projectCompanies} />
          </select>
        </FormField>
      </RecordFilters>

      <RecordTable
        label="Change orders"
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
            <td style={tableCellStyle}>{formatDate(changeOrder.date)}</td>
            <td style={tableCellStyle}>{changeOrder.co_number}</td>
            <td style={tableCellStyle}>{changeOrder.company}</td>
            <td style={tableCellStyle}>
              <StatusBadge value={changeOrder.status} />
            </td>
            <td style={tableCellStyle}>{changeOrder.amount}</td>
            <td style={tableCellStyle}>{changeOrder.responsible_party}</td>
            <td style={tableCellStyle}>{changeOrder.description}</td>
            <td style={tableCellStyle}>
              <button
                type="button"
                className="button-danger"
                onClick={() => onDelete(changeOrder.id)}
                aria-label={`Delete change order ${changeOrder.co_number}`}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default ChangeOrdersPage;
