import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PunchItemsPage from "./PunchItemsPage";

const baseProps = {
  projectName: "North Ridge",
  punchItems: [],
  projectCompanies: [{ id: 1, name: "Desert Drywall" }],
  editingPunchItemId: null,
  editingPunchItemNumber: "",
  location: "",
  trade: "",
  description: "",
  responsibleCompany: "",
  assignedTo: "",
  priority: "Medium",
  status: "Open",
  dueDate: "",
  completedDate: "",
  formatDate: (value) => value || "-",
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  onRefresh: vi.fn(),
  onSave: vi.fn(),
  onEdit: vi.fn(),
  onCancelEdit: vi.fn(),
  onDelete: vi.fn(),
  onLocationChange: vi.fn(),
  onTradeChange: vi.fn(),
  onDescriptionChange: vi.fn(),
  onResponsibleCompanyChange: vi.fn(),
  onAssignedToChange: vi.fn(),
  onPriorityChange: vi.fn(),
  onStatusChange: vi.fn(),
  onDueDateChange: vi.fn(),
  onCompletedDateChange: vi.fn(),
};

const statuses = ["Open", "In Progress", "Completed", "Verified"];
const priorities = ["Low", "Medium", "High", "Critical"];
const records = statuses.map((status, index) => ({
  id: index + 1,
  project_id: 1,
  number: `PUNCH-00${index + 1}`,
  location: `Level ${index + 1}`,
  trade: index === 0 ? "Drywall" : null,
  description: `${status} wall repair`,
  responsible_company: index === 0 ? "Desert Drywall" : null,
  assigned_to: index === 0 ? "A. Rivera" : null,
  priority: priorities[index],
  status,
  due_date: "2000-01-01",
  completed_date: status === "Completed" ? "2026-07-20" : null,
}));

describe("PunchItemsPage", () => {
  it("announces loading and then presents the empty state", () => {
    const { rerender } = render(
      <PunchItemsPage {...baseProps} isLoading />
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading Punch Items..."
    );

    rerender(<PunchItemsPage {...baseProps} />);

    expect(
      screen.getByText(
        "No punch items yet. Create the first punch item above."
      )
    ).toBeInTheDocument();
  });

  it("renders every field, priority, status, and accessible action", () => {
    render(<PunchItemsPage {...baseProps} punchItems={records} />);

    const tableRegion = screen.getByRole("region", {
      name: "Project punch items",
    });

    expect(within(tableRegion).getByText("PUNCH-001")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Level 1")).toBeInTheDocument();
    expect(within(tableRegion).getByText("Drywall")).toBeInTheDocument();
    expect(
      within(tableRegion).getByText("Desert Drywall")
    ).toBeInTheDocument();
    expect(within(tableRegion).getByText("A. Rivera")).toBeInTheDocument();

    for (const value of [...statuses, ...priorities]) {
      expect(
        within(tableRegion)
          .getAllByText(value)
          .some((element) => element.classList.contains("status-badge"))
      ).toBe(true);
    }

    expect(
      screen.getByRole("button", { name: "Edit PUNCH-001" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete PUNCH-001" })
    ).toBeInTheDocument();
  });

  it("marks only active past-due punch items as overdue", () => {
    render(<PunchItemsPage {...baseProps} punchItems={records} />);

    expect(screen.getAllByText("Overdue")).toHaveLength(2);
  });

  it("requires location and description and constrains completed date", () => {
    render(<PunchItemsPage {...baseProps} dueDate="2026-07-25" />);

    expect(screen.getByLabelText("Location *")).toBeRequired();
    expect(screen.getByLabelText("Description *")).toBeRequired();
    expect(screen.getByLabelText("Priority")).toHaveValue("Medium");
    expect(screen.getByLabelText("Status")).toHaveValue("Open");
    expect(screen.getByLabelText("Completed date")).toHaveAttribute(
      "min",
      "2026-07-25"
    );
  });
});
