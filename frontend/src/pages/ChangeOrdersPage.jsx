import ProjectPageLayout from "../components/ProjectPageLayout";
import RecordTable from "../components/RecordTable";
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
}) {
  return (
    <ProjectPageLayout title={`${projectName} Change Orders`} onBack={onBack}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h3>Create Change Order</h3>

        <input
          type="date"
          value={changeOrderDate}
          onChange={(event) => onDateChange(event.target.value)}
        />
        <input
          placeholder="CO Number"
          value={changeOrderNumber}
          onChange={(event) => onNumberChange(event.target.value)}
        />
        <select
          value={changeOrderCompany}
          onChange={(event) => onCompanyChange(event.target.value)}
        >
          <option value="">Select Company</option>
          <CompanyOptions companies={projectCompanies} />
        </select>
        <select
          value={changeOrderStatus}
          onChange={(event) => onStatusChange(event.target.value)}
        >
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
          <option value="Void">Void</option>
        </select>
        <input
          placeholder="Amount"
          value={changeOrderAmount}
          onChange={(event) => onAmountChange(event.target.value)}
        />
        <select
          value={changeOrderResponsibleParty}
          onChange={(event) => onResponsiblePartyChange(event.target.value)}
        >
          <option value="">Responsible Party</option>
          <CompanyOptions companies={projectCompanies} />
        </select>
        <textarea
          placeholder="Description"
          value={changeOrderDescription}
          onChange={(event) => onDescriptionChange(event.target.value)}
        />

        <button onClick={onCreate} style={buttonStyle}>
          Save Change Order
        </button>
      </div>

      <button
        onClick={onRefresh}
        style={{ ...buttonStyle, marginTop: "15px" }}
      >
        Refresh Change Orders
      </button>

      <RecordTable
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
        {changeOrders.map((changeOrder) => (
          <tr key={changeOrder.id}>
            <td style={tableCellStyle}>{formatDate(changeOrder.date)}</td>
            <td style={tableCellStyle}>{changeOrder.co_number}</td>
            <td style={tableCellStyle}>{changeOrder.company}</td>
            <td style={tableCellStyle}>{changeOrder.status}</td>
            <td style={tableCellStyle}>{changeOrder.amount}</td>
            <td style={tableCellStyle}>{changeOrder.responsible_party}</td>
            <td style={tableCellStyle}>{changeOrder.description}</td>
            <td style={tableCellStyle}>
              <button onClick={() => onDelete(changeOrder.id)}>Delete</button>
            </td>
          </tr>
        ))}
      </RecordTable>
    </ProjectPageLayout>
  );
}

export default ChangeOrdersPage;
