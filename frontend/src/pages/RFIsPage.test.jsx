import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RFIsPage from "./RFIsPage";


const baseProps = {
  projectName: "North Ridge",
  rfis: [],
  projectCompanies: [{ id: 1, name: "Desert Glass" }],
  editingRFIId: null,
  editingRFINumber: "",
  rfiSubject: "",
  rfiQuestion: "",
  rfiResponsibleCompany: "",
  rfiSubmittedDate: "2026-07-25",
  rfiDueDate: "",
  rfiResponse: "",
  rfiStatus: "Open",
  formatDate: (value) => value || "-",
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  onRefresh: vi.fn(),
  onSave: vi.fn(),
  onEdit: vi.fn(),
  onCancelEdit: vi.fn(),
  onDelete: vi.fn(),
  onSubjectChange: vi.fn(),
  onQuestionChange: vi.fn(),
  onResponsibleCompanyChange: vi.fn(),
  onSubmittedDateChange: vi.fn(),
  onDueDateChange: vi.fn(),
  onResponseChange: vi.fn(),
  onStatusChange: vi.fn(),
};

const records = [
  {
    id: 1,
    project_id: 1,
    number: "RFI-001",
    subject: "Confirm storefront dimensions",
    question: "Which rough opening dimensions should be used?",
    responsible_company: "Desert Glass",
    submitted_date: "2026-07-20",
    due_date: "2000-01-01",
    response: null,
    status: "Open",
  },
  {
    id: 2,
    project_id: 1,
    number: "RFI-002",
    subject: "Confirm finish color",
    question: "Which finish should be used?",
    responsible_company: null,
    submitted_date: "2026-07-21",
    due_date: "2000-01-02",
    response: "Use dark bronze.",
    status: "Closed",
  },
  {
    id: 3,
    project_id: 1,
    number: "RFI-003",
    subject: "Confirm hardware set",
    question: "Which hardware set applies?",
    responsible_company: "Valley Doors",
    submitted_date: "2026-07-22",
    due_date: null,
    response: null,
    status: "Pending",
  },
];


describe("RFIsPage", () => {
  it("announces loading and then presents the empty state", () => {
    const { rerender } = render(<RFIsPage {...baseProps} isLoading />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading RFIs...");

    rerender(<RFIsPage {...baseProps} />);

    expect(
      screen.getByText("No RFIs yet. Create the first RFI above.")
    ).toBeInTheDocument();
  });

  it("renders populated records with accessible status and response text", () => {
    render(<RFIsPage {...baseProps} rfis={records} />);

    const tableRegion = screen.getByRole("region", {
      name: "Requests for information",
    });

    expect(within(tableRegion).getByText("RFI-001")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Open")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Pending")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Closed")).toBeInTheDocument();
    expect(
      within(tableRegion).getAllByText("Awaiting response")
    ).toHaveLength(2);
    expect(within(tableRegion).getByText("Use dark bronze.")).toBeInTheDocument();
  });

  it("marks only unresolved past-due RFIs as overdue", () => {
    render(<RFIsPage {...baseProps} rfis={records} />);

    expect(screen.getAllByText("Overdue")).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "Edit RFI-001" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete RFI-001" })
    ).toBeInTheDocument();
  });

  it("exposes required controls and the submitted-date minimum", () => {
    render(<RFIsPage {...baseProps} />);

    expect(screen.getByLabelText("Subject *")).toBeRequired();
    expect(screen.getByLabelText("Question *")).toBeRequired();
    expect(screen.getByLabelText("Submitted date *")).toBeRequired();
    expect(screen.getByLabelText("Due date")).toHaveAttribute(
      "min",
      "2026-07-25"
    );
  });
});
