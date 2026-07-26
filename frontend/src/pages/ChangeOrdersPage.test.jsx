import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CHANGE_ORDER_STATUSES } from "../utils/changeOrder";
import ChangeOrdersPage from "./ChangeOrdersPage";

const baseProps = {
  projectName: "North Ridge",
  changeOrders: [],
  projectCompanies: [{ id: 1, name: "Desert Concrete" }],
  editingChangeOrderId: null,
  editingChangeOrderNumber: "",
  changeOrderDate: "2026-07-26",
  changeOrderTitle: "",
  changeOrderCompany: "",
  changeOrderStatus: "Pending",
  changeOrderDescription: "",
  changeOrderReason: "",
  changeOrderProposedAmount: "",
  changeOrderApprovedAmount: "",
  changeOrderScheduleImpactDays: "",
  changeOrderRequestedDate: "",
  changeOrderSubmittedDate: "",
  changeOrderApprovedDate: "",
  changeOrderExecutedDate: "",
  changeOrderResponsibleParty: "",
  formatDate: (value) => value || "Not specified",
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  onRefresh: vi.fn(),
  onSave: vi.fn(),
  onEdit: vi.fn(),
  onCancelEdit: vi.fn(),
  onDelete: vi.fn(),
  onDateChange: vi.fn(),
  onTitleChange: vi.fn(),
  onCompanyChange: vi.fn(),
  onStatusChange: vi.fn(),
  onDescriptionChange: vi.fn(),
  onReasonChange: vi.fn(),
  onProposedAmountChange: vi.fn(),
  onApprovedAmountChange: vi.fn(),
  onScheduleImpactDaysChange: vi.fn(),
  onRequestedDateChange: vi.fn(),
  onSubmittedDateChange: vi.fn(),
  onApprovedDateChange: vi.fn(),
  onExecutedDateChange: vi.fn(),
  onResponsiblePartyChange: vi.fn(),
};

const enhancedRecord = {
  id: 1,
  project_id: 1,
  date: "2026-07-20",
  co_number: "CO-001",
  company: "Desert Concrete",
  status: "Under Review",
  title: "North entrance revision",
  description: "Revise curb and drainage.",
  reason: "Owner request",
  amount: "1250",
  proposed_amount: "1250.00",
  approved_amount: "1000.50",
  schedule_impact_days: 5,
  requested_date: "2026-07-20",
  submitted_date: "2026-07-21",
  approved_date: null,
  executed_date: null,
  responsible_party: "Desert Concrete",
};

const legacyRecord = {
  id: 2,
  project_id: 1,
  date: "2026-06-01",
  co_number: "3",
  company: null,
  status: "Legacy Review",
  title: null,
  description: "Legacy change order",
  reason: null,
  amount: "$4,500",
  proposed_amount: null,
  approved_amount: null,
  schedule_impact_days: null,
  requested_date: null,
  submitted_date: null,
  approved_date: null,
  executed_date: null,
  responsible_party: null,
};

describe("ChangeOrdersPage", () => {
  it("announces loading and then presents the empty state", () => {
    const { rerender } = render(
      <ChangeOrdersPage {...baseProps} isLoading />
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading change orders..."
    );

    rerender(<ChangeOrdersPage {...baseProps} />);

    expect(
      screen.getByText(
        "No change orders yet. Create the first change order above."
      )
    ).toBeInTheDocument();
  });

  it("renders enhanced and legacy records without rewriting their values", () => {
    render(
      <ChangeOrdersPage
        {...baseProps}
        changeOrders={[enhancedRecord, legacyRecord]}
      />
    );

    const table = screen.getByRole("region", { name: "Change orders" });

    expect(within(table).getByText("CO-001")).toBeInTheDocument();
    expect(within(table).getByText("3")).toBeInTheDocument();
    expect(within(table).getByText("$1,250.00")).toBeInTheDocument();
    expect(within(table).getByText("$1,000.50")).toBeInTheDocument();
    expect(within(table).getByText("+5 days")).toBeInTheDocument();
    expect(within(table).getByText("$4,500")).toBeInTheDocument();
    expect(
      within(table).getByText("Untitled change order")
    ).toBeInTheDocument();
    expect(within(table).getByText("Legacy Review")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Edit change order 3" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete change order 3" })
    ).toBeInTheDocument();
  });

  it("exposes all statuses, labeled controls, and a read-only number", () => {
    render(<ChangeOrdersPage {...baseProps} />);

    expect(screen.getByLabelText("Record date *")).toBeRequired();
    expect(screen.getByLabelText("Change order number")).toHaveAttribute(
      "readonly"
    );
    expect(screen.getByLabelText("Change order number")).toHaveValue(
      "Assigned when saved"
    );
    expect(screen.getByLabelText("Submitted date")).not.toBeRequired();
    expect(screen.getByLabelText("Approved date")).not.toBeRequired();

    const status = screen.getByLabelText("Status", {
      selector: "#change-order-status",
    });
    expect(
      within(status).getAllByRole("option").map((option) => option.value)
    ).toEqual(CHANGE_ORDER_STATUSES);
  });

  it("sets lifecycle minimums from the final form state", () => {
    render(
      <ChangeOrdersPage
        {...baseProps}
        changeOrderRequestedDate="2026-07-20"
        changeOrderSubmittedDate="2026-07-21"
        changeOrderApprovedDate="2026-07-22"
      />
    );

    expect(screen.getByLabelText("Submitted date")).toHaveAttribute(
      "min",
      "2026-07-20"
    );
    expect(screen.getByLabelText("Approved date")).toHaveAttribute(
      "min",
      "2026-07-21"
    );
    expect(screen.getByLabelText("Executed date")).toHaveAttribute(
      "min",
      "2026-07-22"
    );
  });

  it("filters every supported status while retaining an All option", async () => {
    const user = userEvent.setup();
    const records = CHANGE_ORDER_STATUSES.map((status, index) => ({
      ...enhancedRecord,
      id: index + 1,
      co_number: `CO-00${index + 1}`,
      status,
    }));

    render(<ChangeOrdersPage {...baseProps} changeOrders={records} />);

    const filter = screen.getByLabelText("Status", {
      selector: "#change-order-status-filter",
    });
    expect(within(filter).getByRole("option", {
      name: "All statuses",
    })).toBeInTheDocument();

    for (const status of CHANGE_ORDER_STATUSES) {
      await user.selectOptions(filter, status);
      expect(screen.getByText("1 record")).toBeInTheDocument();
      expect(
        within(screen.getByRole("region", { name: "Change orders" }))
          .getAllByText(status)
          .some((element) => element.classList.contains("status-badge"))
      ).toBe(true);
    }
  });

  it("enters edit mode with a read-only legacy number and supports cancel", async () => {
    const user = userEvent.setup();
    const onCancelEdit = vi.fn();

    render(
      <ChangeOrdersPage
        {...baseProps}
        editingChangeOrderId={2}
        editingChangeOrderNumber="3"
        changeOrderStatus="Legacy Review"
        changeOrderTitle="Legacy title"
        onCancelEdit={onCancelEdit}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Edit 3" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Change order number")).toHaveValue("3");
    expect(
      within(screen.getByLabelText("Status", {
        selector: "#change-order-status",
      })).getByRole("option", { name: "Legacy Review" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel Edit" }));
    expect(onCancelEdit).toHaveBeenCalledOnce();
  });
});
