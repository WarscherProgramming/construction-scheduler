import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDashboardPage from "./ProjectDashboardPage";


const hookMocks = vi.hoisted(() => ({
  useProjectDashboard: vi.fn(),
}));

vi.mock("../hooks/useProjectDashboard", () => ({
  default: hookMocks.useProjectDashboard,
}));


const DASHBOARD = {
  as_of: "2026-07-27",
  generated_at: "2026-07-27T23:00:00Z",
  project: { id: 1, name: "Apex Clubhouse" },
  schedule: {
    task_count: 18,
    planned_start: "2026-01-01",
    planned_finish: "2026-12-15",
    past_planned_finish_count: 3,
    upcoming_start_count: 4,
  },
  rfis: { total: 7, open: 5, overdue: 2, due_soon: 1 },
  submittals: { total: 9, pending: 4, overdue: 1, due_soon: 2 },
  punch_items: {
    total: 12,
    open: 6,
    overdue: 3,
    completed_last_7_days: 2,
  },
  change_orders: {
    total: 5,
    active: 2,
    approved: 2,
    rejected: 1,
    unknown_status: 0,
    active_value: "1234567.89",
    approved_value: "100.30",
  },
  daily_logs: {
    total: 20,
    latest_log_date: "2026-07-27",
    today_count: 2,
    today_manpower: 17,
    last_7_days_count: 6,
  },
  documents: {
    total: 10,
    uploaded_last_7_days: 3,
    recent: [],
  },
  attention_items: [],
  upcoming_tasks: [],
  recent_updates: [],
};

const BASE_PROPS = {
  projectId: 1,
  projectName: "Loading project",
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  onRequestError: vi.fn(),
};


describe("ProjectDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: DASHBOARD,
      isLoading: false,
      error: null,
      retry: vi.fn(),
      asOf: "2026-07-27",
    });
  });

  it("renders one project-focused heading and local date context", () => {
    render(<ProjectDashboardPage {...BASE_PROPS} />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { name: "Project Dashboard" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("Apex Clubhouse").length).toBeGreaterThan(0);
    expect(screen.getByText("July 27, 2026")).toHaveAttribute(
      "datetime",
      "2026-07-27"
    );
  });

  it("renders reliable aggregate metrics without legacy health claims", () => {
    render(<ProjectDashboardPage {...BASE_PROPS} />);

    expect(screen.getByLabelText("Past Planned Finish: 3")).toBeInTheDocument();
    expect(screen.getByLabelText("Upcoming Starts: 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Open RFIs: 5")).toBeInTheDocument();
    expect(screen.getByLabelText("Overdue RFIs: 2")).toBeInTheDocument();
    expect(screen.getByLabelText("Pending Submittals: 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Open Punch Items: 6")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Active Change Order Value: $1,234,567.89")
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Approved Change Order Value: $100.30")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Today's Daily Logs: 2")).toBeInTheDocument();
    expect(screen.getByLabelText("Documents Uploaded: 3")).toBeInTheDocument();
    expect(screen.queryByText(/project health/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/schedule health/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/critical activities/i)).not.toBeInTheDocument();
  });

  it("uses explicit page-level links for supported resources", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(
      <ProjectDashboardPage
        {...BASE_PROPS}
        onNavigate={onNavigate}
      />
    );

    const rfiLink = screen.getByRole("link", {
      name: "View RFIs from Open RFIs summary",
    });
    rfiLink.focus();
    expect(rfiLink).toHaveFocus();
    expect(rfiLink).toHaveAttribute("href", "#/projects/1/rfis");
    await user.click(rfiLink);
    await user.click(
      screen.getByRole("link", {
        name: "View Change Orders from Active Change Order Value summary",
      })
    );

    expect(onNavigate.mock.calls).toEqual([["rfis"], ["changeOrders"]]);
  });

  it("composes actionable lists beneath unchanged summary metrics", () => {
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: {
        ...DASHBOARD,
        attention_items: [
          {
            resource_type: "rfi",
            record_id: 17,
            identifier: "RFI-017",
            title: "Clarify storefront flashing",
            due_date: "2026-07-24",
            reason: "Overdue",
            severity: "overdue",
            target_page: "rfis",
          },
        ],
        upcoming_tasks: [
          {
            id: 12,
            name: "Install storefront",
            start_date: "2026-07-29",
            end_date: "2026-08-02",
            duration: 5,
          },
        ],
        recent_updates: [
          {
            resource_type: "rfi",
            record_id: 17,
            identifier: "RFI-017",
            description: "Recently clarified storefront flashing",
            updated_at: "2026-07-27T23:00:00Z",
            target_page: "rfis",
          },
        ],
      },
      isLoading: false,
      error: null,
      retry: vi.fn(),
      asOf: "2026-07-27",
    });

    render(<ProjectDashboardPage {...BASE_PROPS} />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { level: 2, name: "Attention Required" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Upcoming Schedule" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Workflow Analytics" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Recent Updates" })
    ).toBeInTheDocument();
    expect(screen.getByText("Clarify storefront flashing")).toBeInTheDocument();
    expect(screen.getByText("Install storefront")).toBeInTheDocument();
    expect(
      screen.getByText("Recently clarified storefront flashing")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Open RFIs: 5")).toBeInTheDocument();

    const linkNames = screen.getAllByRole("link").map(
      (link) => link.getAttribute("aria-label") || link.textContent
    );
    expect(new Set(linkNames).size).toBe(linkNames.length);
  });

  it("preserves the header and summary structure while loading", () => {
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: null,
      isLoading: true,
      error: null,
      retry: vi.fn(),
      asOf: "2026-07-27",
    });

    const { container } = render(
      <ProjectDashboardPage {...BASE_PROPS} />
    );

    expect(
      screen.getByRole("heading", { name: "Project Dashboard" })
    ).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole("heading", { level: 2 })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading project summary"
    );
    expect(screen.queryByText("Project Summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Attention Required")).not.toBeInTheDocument();
    expect(screen.queryByText("Upcoming Schedule")).not.toBeInTheDocument();
    expect(screen.queryByText("Workflow Analytics")).not.toBeInTheDocument();
    expect(screen.queryByText("Recent Updates")).not.toBeInTheDocument();
    expect(
      container.querySelectorAll(".dashboard-action-section--loading")
    ).toHaveLength(2);
    expect(
      container.querySelectorAll(".dashboard-action-skeleton-row")
    ).toHaveLength(6);
    expect(
      container.querySelectorAll(".dashboard-workflow-card")
    ).toHaveLength(4);
    expect(
      container.querySelectorAll(".dashboard-recent-update-skeleton")
    ).toHaveLength(3);
  });

  it("replaces metrics with an accessible retry state after failure", async () => {
    const user = userEvent.setup();
    const retry = vi.fn();
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: null,
      isLoading: false,
      error: new Error("Service unavailable"),
      retry,
      asOf: "2026-07-27",
    });

    render(<ProjectDashboardPage {...BASE_PROPS} />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Project dashboard data could not be loaded"
    );
    expect(screen.queryByText("Open RFIs")).not.toBeInTheDocument();
    expect(screen.queryByText("Attention Required")).not.toBeInTheDocument();
    expect(screen.queryByText("Upcoming Schedule")).not.toBeInTheDocument();
    expect(screen.queryByText("Workflow Analytics")).not.toBeInTheDocument();
    expect(screen.queryByText("Recent Updates")).not.toBeInTheDocument();
    const retryButton = screen.getByRole("button", {
      name: "Retry dashboard",
    });
    retryButton.focus();
    expect(retryButton).toHaveFocus();
    await user.click(retryButton);
    expect(retry).toHaveBeenCalledOnce();
  });

  it("distinguishes no project and reliable zero metrics from errors", () => {
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: null,
      isLoading: false,
      error: null,
      retry: vi.fn(),
      asOf: "2026-07-27",
    });
    const { rerender } = render(
      <ProjectDashboardPage {...BASE_PROPS} projectId={null} />
    );
    expect(
      screen.getByText("Select a project to view its dashboard")
    ).toBeInTheDocument();

    const emptyDashboard = {
      ...DASHBOARD,
      schedule: {
        ...DASHBOARD.schedule,
        task_count: 0,
        past_planned_finish_count: 0,
        upcoming_start_count: 0,
      },
      rfis: { total: 0, open: 0, overdue: 0, due_soon: 0 },
      submittals: { total: 0, pending: 0, overdue: 0, due_soon: 0 },
      punch_items: {
        total: 0,
        open: 0,
        overdue: 0,
        completed_last_7_days: 0,
      },
      change_orders: {
        ...DASHBOARD.change_orders,
        total: 0,
        active: 0,
        approved: 0,
        active_value: "0.00",
        approved_value: "0.00",
      },
      daily_logs: {
        ...DASHBOARD.daily_logs,
        total: 0,
        today_count: 0,
        today_manpower: 0,
      },
      documents: {
        ...DASHBOARD.documents,
        total: 0,
        uploaded_last_7_days: 0,
      },
    };
    hookMocks.useProjectDashboard.mockReturnValue({
      dashboard: emptyDashboard,
      isLoading: false,
      error: null,
      retry: vi.fn(),
      asOf: "2026-07-27",
    });

    rerender(<ProjectDashboardPage {...BASE_PROPS} />);

    expect(screen.getByLabelText("Open RFIs: 0")).toBeInTheDocument();
    expect(
      screen.getAllByText("No RFIs have been added.")
    ).toHaveLength(3);
    expect(
      screen.getByLabelText("Active Change Order Value: $0.00")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "No attention items were identified for this dashboard date."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "No schedule tasks have been added to this project."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("No recent record updates are available.")
    ).toBeInTheDocument();
    expect(screen.queryByText(/all clear|on track|no risk/i)).not.toBeInTheDocument();
  });
});
