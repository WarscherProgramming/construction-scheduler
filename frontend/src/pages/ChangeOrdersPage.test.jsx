import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ChangeOrdersPage from "./ChangeOrdersPage";


const baseProps = {
  projectName: "North Ridge",
  projectCompanies: [{ id: 1, name: "Desert Concrete" }],
  changeOrderDate: "2026-06-20",
  changeOrderNumber: "",
  changeOrderCompany: "",
  changeOrderStatus: "Pending",
  changeOrderDescription: "",
  changeOrderAmount: "",
  changeOrderResponsibleParty: "",
  formatDate: (value) => value,
  onBack: vi.fn(),
  onRefresh: vi.fn(),
  onCreate: vi.fn(),
  onDelete: vi.fn(),
  onDateChange: vi.fn(),
  onNumberChange: vi.fn(),
  onCompanyChange: vi.fn(),
  onStatusChange: vi.fn(),
  onDescriptionChange: vi.fn(),
  onAmountChange: vi.fn(),
  onResponsiblePartyChange: vi.fn(),
};


describe("ChangeOrdersPage", () => {
  it("filters change orders by status", async () => {
    const user = userEvent.setup();

    render(
      <ChangeOrdersPage
        {...baseProps}
        changeOrders={[
          {
            id: 1,
            date: "2026-06-20",
            co_number: "CO-101",
            company: "Desert Concrete",
            status: "Pending",
            amount: "1500",
            responsible_party: "Desert Concrete",
            description: "Added curb",
          },
          {
            id: 2,
            date: "2026-06-19",
            co_number: "CO-102",
            company: "Desert Concrete",
            status: "Approved",
            amount: "900",
            responsible_party: "Desert Concrete",
            description: "Gate revision",
          },
        ]}
      />
    );

    await user.selectOptions(
      screen.getByLabelText("Status", { selector: "#change-order-status-filter" }),
      "Approved"
    );

    expect(screen.getByText("CO-102")).toBeInTheDocument();
    expect(screen.queryByText("CO-101")).not.toBeInTheDocument();
    expect(screen.getByText("1 record")).toBeInTheDocument();
  });
});
