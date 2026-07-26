import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SubmittalsPage from "./SubmittalsPage";

const baseProps = {
  projectName: "North Ridge",
  submittals: [],
  projectCompanies: [{ id: 1, name: "Desert Glass" }],
  editingSubmittalId: null,
  editingSubmittalNumber: "",
  specificationSection: "",
  title: "",
  responsibleCompany: "",
  submittedDate: "",
  requiredByDate: "",
  reviewedDate: "",
  status: "Draft",
  reviewer: "",
  remarks: "",
  formatDate: (value) => value || "-",
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  onRefresh: vi.fn(),
  onSave: vi.fn(),
  onEdit: vi.fn(),
  onCancelEdit: vi.fn(),
  onDelete: vi.fn(),
  onSpecificationSectionChange: vi.fn(),
  onTitleChange: vi.fn(),
  onResponsibleCompanyChange: vi.fn(),
  onSubmittedDateChange: vi.fn(),
  onRequiredByDateChange: vi.fn(),
  onReviewedDateChange: vi.fn(),
  onStatusChange: vi.fn(),
  onReviewerChange: vi.fn(),
  onRemarksChange: vi.fn(),
};

const statuses = [
  "Draft",
  "Submitted",
  "Under Review",
  "Approved",
  "Revise and Resubmit",
  "Rejected",
];

const records = statuses.map((status, index) => ({
  id: index + 1,
  project_id: 1,
  number: `SUB-00${index + 1}`,
  specification_section: `08 4${index} 00`,
  title: `${status} storefront package`,
  responsible_company: index === 0 ? "Desert Glass" : null,
  submitted_date: index === 0 ? null : "2026-07-20",
  required_by_date: "2000-01-01",
  reviewed_date: status === "Approved" ? "2026-07-22" : null,
  status,
  reviewer: status === "Approved" ? "Design Team" : null,
  remarks: index === 0 ? "Initial package" : null,
}));

describe("SubmittalsPage", () => {
  it("announces loading and then presents the empty state", () => {
    const { rerender } = render(
      <SubmittalsPage {...baseProps} isLoading />
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading Submittals..."
    );

    rerender(<SubmittalsPage {...baseProps} />);

    expect(
      screen.getByText(
        "No submittals yet. Create the first submittal above."
      )
    ).toBeInTheDocument();
  });

  it("renders every field and workflow status with accessible actions", () => {
    render(<SubmittalsPage {...baseProps} submittals={records} />);

    const tableRegion = screen.getByRole("region", {
      name: "Project submittals",
    });

    expect(within(tableRegion).getByText("SUB-001")).toBeInTheDocument();
    expect(within(tableRegion).getByText("08 40 00")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Desert Glass")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Initial package")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Design Team")).toBeInTheDocument();

    for (const status of statuses) {
      expect(
        within(tableRegion)
          .getAllByText(status)
          .some((element) => element.classList.contains("status-badge"))
      ).toBe(true);
    }

    expect(
      screen.getByRole("button", { name: "Edit SUB-001" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete SUB-001" })
    ).toBeInTheDocument();
  });

  it("marks only unresolved past-due submittals as overdue", () => {
    render(<SubmittalsPage {...baseProps} submittals={records} />);

    expect(screen.getAllByText("Overdue")).toHaveLength(3);
  });

  it("requires title and specification section while dates remain optional", () => {
    render(
      <SubmittalsPage
        {...baseProps}
        submittedDate="2026-07-25"
      />
    );

    expect(screen.getByLabelText("Specification section *")).toBeRequired();
    expect(screen.getByLabelText("Title *")).toBeRequired();
    expect(screen.getByLabelText("Submitted date")).not.toBeRequired();
    expect(screen.getByLabelText("Required-by date")).toHaveAttribute(
      "min",
      "2026-07-25"
    );
    expect(screen.getByLabelText("Reviewed date")).toHaveAttribute(
      "min",
      "2026-07-25"
    );
  });
});
