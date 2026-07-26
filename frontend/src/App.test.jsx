import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./services/api", () => ({
  fetchProjects: vi.fn(),
  createProject: vi.fn(),
  fetchTasks: vi.fn(),
  createTask: vi.fn(),
  deleteTask: vi.fn(),
  updateTask: vi.fn(),
  fetchTemplates: vi.fn(),
  saveTemplate: vi.fn(),
  applyTemplate: vi.fn(),
  exportProjectPdf: vi.fn(),
  fetchDailyLogs: vi.fn(),
  createDailyLog: vi.fn(),
  fetchInspections: vi.fn(),
  createInspection: vi.fn(),
  fetchNotesDelays: vi.fn(),
  createNoteDelay: vi.fn(),
  fetchChangeOrders: vi.fn(),
  createChangeOrder: vi.fn(),
  updateChangeOrder: vi.fn(),
  fetchProjectCompanies: vi.fn(),
  createProjectCompany: vi.fn(),
  deleteChangeOrder: vi.fn(),
  fetchRFIs: vi.fn(),
  createRFI: vi.fn(),
  updateRFI: vi.fn(),
  deleteRFI: vi.fn(),
  fetchSubmittals: vi.fn(),
  createSubmittal: vi.fn(),
  updateSubmittal: vi.fn(),
  deleteSubmittal: vi.fn(),
  fetchPunchItems: vi.fn(),
  createPunchItem: vi.fn(),
  updatePunchItem: vi.fn(),
  deletePunchItem: vi.fn(),
  reorderTasks: vi.fn(),
  loginUser: vi.fn(),
  registerUser: vi.fn(),
}));

vi.mock("./services/demoSeeder", () => ({
  seedDemoProject: vi.fn(),
}));

import App from "./App";
import AuthProvider from "./auth/AuthProvider";
import {
  createChangeOrder,
  createRFI,
  createPunchItem,
  createSubmittal,
  deleteChangeOrder,
  deletePunchItem,
  deleteRFI,
  deleteSubmittal,
  fetchChangeOrders,
  fetchDailyLogs,
  fetchInspections,
  fetchNotesDelays,
  fetchPunchItems,
  fetchProjectCompanies,
  fetchProjects,
  fetchRFIs,
  fetchSubmittals,
  fetchTasks,
  fetchTemplates,
  updateRFI,
  updateChangeOrder,
  updatePunchItem,
  updateSubmittal,
} from "./services/api";
import { ApiError } from "./services/httpClient";

function renderApp() {
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

function makeChangeOrder(overrides = {}) {
  return {
    id: 1,
    project_id: 1,
    date: "2026-07-20",
    co_number: "CO-001",
    company: "Desert Concrete",
    status: "Pending",
    description: "Revise north entrance.",
    amount: null,
    responsible_party: "Desert Concrete",
    title: "North entrance revision",
    reason: null,
    proposed_amount: "1250.00",
    approved_amount: null,
    schedule_impact_days: 2,
    requested_date: "2026-07-20",
    submitted_date: null,
    approved_date: null,
    executed_date: null,
    created_at: "2026-07-26T12:00:00Z",
    updated_at: "2026-07-26T12:00:00Z",
    ...overrides,
  };
}

describe("App integration (hooks wiring)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("token", "integration-token");
    window.location.hash = "";

    fetchProjects.mockResolvedValue({ projects: [] });
    fetchTemplates.mockResolvedValue({ templates: [] });
    fetchTasks.mockResolvedValue({ tasks: [] });
    fetchProjectCompanies.mockResolvedValue({ companies: [] });
    fetchDailyLogs.mockResolvedValue({ daily_logs: [] });
    fetchInspections.mockResolvedValue({ inspections: [] });
    fetchNotesDelays.mockResolvedValue({ notes_delays: [] });
    fetchChangeOrders.mockResolvedValue({ change_orders: [] });
    createChangeOrder.mockResolvedValue({});
    updateChangeOrder.mockResolvedValue({});
    deleteChangeOrder.mockResolvedValue({
      message: "Change order deleted",
    });
    fetchRFIs.mockResolvedValue({ rfis: [] });
    createRFI.mockResolvedValue({});
    updateRFI.mockResolvedValue({});
    deleteRFI.mockResolvedValue({ message: "RFI deleted" });
    fetchSubmittals.mockResolvedValue({ submittals: [] });
    createSubmittal.mockResolvedValue({});
    updateSubmittal.mockResolvedValue({});
    deleteSubmittal.mockResolvedValue({ message: "Submittal deleted" });
    fetchPunchItems.mockResolvedValue({ punch_items: [] });
    createPunchItem.mockResolvedValue({});
    updatePunchItem.mockResolvedValue({});
    deletePunchItem.mockResolvedValue({ message: "Punch Item deleted" });
  });

  it("shows the login experience when unauthenticated", () => {
    localStorage.removeItem("token");

    renderApp();

    expect(
      screen.getByRole("heading", { name: "Welcome back" })
    ).toBeInTheDocument();
    expect(fetchProjects).not.toHaveBeenCalled();
    expect(fetchPunchItems).not.toHaveBeenCalled();
  });

  it("loads projects and shows first-run onboarding for an empty account", async () => {
    renderApp();

    expect(
      await screen.findByText("Welcome to FieldFlow")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Load Sample Project" })
    ).toBeInTheDocument();
    expect(fetchProjects).toHaveBeenCalledOnce();
    expect(fetchTemplates).toHaveBeenCalledOnce();
  });

  it("navigates from home to a project dashboard and loads its data", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");

    expect(
      await screen.findByText("Riverside Dashboard")
    ).toBeInTheDocument();
    expect(fetchTasks).toHaveBeenCalledWith(1);
    expect(fetchDailyLogs).toHaveBeenCalledWith(1);
    await screen.findByRole("button", {
      name: "Change Order health: 0 active, 0 approved, 0 rejected, $0.00 proposed cost, $0.00 approved cost, 0 days schedule impact",
    });
    expect(fetchChangeOrders).toHaveBeenCalledTimes(1);
    expect(fetchChangeOrders).toHaveBeenCalledWith(1);
    await screen.findByRole("button", {
      name: "RFI health: 0 open, 0 overdue, 0 closed",
    });
    await screen.findByRole("button", {
      name: "Submittal health: 0 active, 0 overdue, 0 approved",
    });
    await screen.findByRole("button", {
      name: "Punch List health: 0 open, 0 overdue, 0 completed",
    });
    expect(fetchRFIs).toHaveBeenCalledTimes(1);
    expect(fetchRFIs).toHaveBeenCalledWith(1);
    await waitFor(() => {
      expect(fetchSubmittals).toHaveBeenCalledTimes(1);
    });
    expect(fetchSubmittals).toHaveBeenCalledWith(1);
    await waitFor(() => {
      expect(fetchPunchItems).toHaveBeenCalledTimes(1);
    });
    expect(fetchPunchItems).toHaveBeenCalledWith(1);
  });

  it("clears Change Order dashboard metrics while switching projects", async () => {
    const user = userEvent.setup();
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchChangeOrders.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          change_orders: [
            {
              id: 1,
              status: "Draft",
              proposed_amount: "100.25",
              approved_amount: null,
              schedule_impact_days: 5,
            },
          ],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    expect(
      await screen.findByRole("button", {
        name: "Change Order health: 1 active, 0 approved, 0 rejected, $100.25 proposed cost, $0.00 approved cost, +5 days schedule impact",
      })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back to Home" }));
    await user.selectOptions(screen.getByLabelText("Project"), "2");

    expect(
      await screen.findByRole("button", {
        name: "Change Order health, loading",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Change Order health: 1 active, 0 approved, 0 rejected, $100.25 proposed cost, $0.00 approved cost, +5 days schedule impact",
      })
    ).not.toBeInTheDocument();

    await act(async () => {
      resolveSecondProject({
        change_orders: [
          {
            id: 2,
            status: "Approved",
            proposed_amount: "80.00",
            approved_amount: "75.50",
            schedule_impact_days: -2,
          },
        ],
      });
    });

    expect(
      await screen.findByRole("button", {
        name: "Change Order health: 0 active, 1 approved, 0 rejected, $80.00 proposed cost, $75.50 approved cost, -2 days schedule impact",
      })
    ).toBeInTheDocument();
    expect(
      fetchChangeOrders.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("keeps the dashboard usable when Change Orders fail to load", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    expect(
      await screen.findByText(
        "Unable to load change orders. Service unavailable"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
    expect(
      screen.getByRole("button", {
        name: "RFI health: 0 open, 0 overdue, 0 closed",
      })
    ).toBeEnabled();
    expect(fetchChangeOrders).toHaveBeenCalledTimes(1);
  });

  it("navigates from the dashboard KPI to Change Orders", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    const changeOrderKpi = await screen.findByRole("button", {
      name: "Change Order health: 0 active, 0 approved, 0 rejected, $0.00 proposed cost, $0.00 approved cost, 0 days schedule impact",
    });
    expect(fetchChangeOrders).toHaveBeenCalledTimes(1);

    await user.click(changeOrderKpi);

    expect(
      await screen.findByRole("heading", { name: "Change Orders" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/change-orders");
  });

  it("drops a late Change Orders dashboard response after a project switch", async () => {
    let resolveFirstProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchChangeOrders.mockImplementation((projectId) => {
      if (projectId === 1) {
        return new Promise((resolve) => {
          resolveFirstProject = resolve;
        });
      }

      return Promise.resolve({
        change_orders: [
          {
            id: 2,
            status: "Void",
            amount: "$50.00",
            schedule_impact_days: 0,
          },
        ],
      });
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    await waitFor(() => {
      expect(fetchChangeOrders).toHaveBeenCalledWith(1);
    });
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/dashboard");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    expect(
      await screen.findByRole("button", {
        name: "Change Order health, loading",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Change Order health: 1 active, 0 approved, 0 rejected, $999.00 proposed cost, $0.00 approved cost, +10 days schedule impact",
      })
    ).not.toBeInTheDocument();

    await act(async () => {
      resolveFirstProject({
        change_orders: [
          {
            id: 9,
            status: "Pending",
            proposed_amount: "999.00",
            schedule_impact_days: 10,
          },
        ],
      });
    });

    expect(
      await screen.findByRole("button", {
        name: "Change Order health: 0 active, 0 approved, 1 rejected, $50.00 proposed cost, $0.00 approved cost, 0 days schedule impact",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Change Order health: 1 active, 0 approved, 0 rejected, $999.00 proposed cost, $0.00 approved cost, +10 days schedule impact",
      })
    ).not.toBeInTheDocument();
    expect(
      fetchChangeOrders.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("clears RFI dashboard metrics while switching projects", async () => {
    const user = userEvent.setup();
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchRFIs.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          rfis: [{ id: 1, status: "Open", due_date: null }],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    expect(
      await screen.findByRole("button", {
        name: "RFI health: 1 open, 0 overdue, 0 closed",
      })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back to Home" }));
    await user.selectOptions(screen.getByLabelText("Project"), "2");

    expect(
      await screen.findByRole("button", { name: "RFI health, loading" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "RFI health: 1 open, 0 overdue, 0 closed",
      })
    ).not.toBeInTheDocument();

    await act(async () => {
      resolveSecondProject({ rfis: [] });
    });

    expect(
      await screen.findByRole("button", {
        name: "RFI health: 0 open, 0 overdue, 0 closed",
      })
    ).toBeInTheDocument();
    expect(fetchRFIs.mock.calls.map(([projectId]) => projectId)).toEqual([
      1, 2,
    ]);
  });

  it("keeps the dashboard usable when its RFI request fails", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchRFIs.mockRejectedValue(new ApiError("Service unavailable", 503));
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Riverside Dashboard" })
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Unable to load RFIs. Service unavailable")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
  });

  it("clears Submittal dashboard metrics while switching projects", async () => {
    const user = userEvent.setup();
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchSubmittals.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          submittals: [
            {
              id: 1,
              status: "Draft",
              required_by_date: null,
            },
          ],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    expect(
      await screen.findByRole("button", {
        name: "Submittal health: 1 active, 0 overdue, 0 approved",
      })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back to Home" }));
    await user.selectOptions(screen.getByLabelText("Project"), "2");

    expect(
      await screen.findByRole("button", {
        name: "Submittal health, loading",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Submittal health: 1 active, 0 overdue, 0 approved",
      })
    ).not.toBeInTheDocument();

    await act(async () => {
      resolveSecondProject({ submittals: [] });
    });

    expect(
      await screen.findByRole("button", {
        name: "Submittal health: 0 active, 0 overdue, 0 approved",
      })
    ).toBeInTheDocument();
    expect(
      fetchSubmittals.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("keeps the dashboard usable when its Submittals request fails", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchSubmittals.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Riverside Dashboard" })
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Unable to load Submittals. Service unavailable"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
    expect(fetchSubmittals).toHaveBeenCalledTimes(1);
  });

  it("navigates from the dashboard KPI to Submittals", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    const submittalKpi = await screen.findByRole("button", {
      name: "Submittal health: 0 active, 0 overdue, 0 approved",
    });
    expect(fetchSubmittals).toHaveBeenCalledTimes(1);

    await user.click(submittalKpi);

    expect(
      await screen.findByRole("heading", { name: "Submittals" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/submittals");
  });

  it("clears Punch List dashboard metrics while switching projects", async () => {
    const user = userEvent.setup();
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchPunchItems.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          punch_items: [
            {
              id: 1,
              status: "Open",
              due_date: null,
            },
          ],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    expect(
      await screen.findByRole("button", {
        name: "Punch List health: 1 open, 0 overdue, 0 completed",
      })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back to Home" }));
    await user.selectOptions(screen.getByLabelText("Project"), "2");

    expect(
      await screen.findByRole("button", {
        name: "Punch List health, loading",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Punch List health: 1 open, 0 overdue, 0 completed",
      })
    ).not.toBeInTheDocument();

    await act(async () => {
      resolveSecondProject({ punch_items: [] });
    });

    expect(
      await screen.findByRole("button", {
        name: "Punch List health: 0 open, 0 overdue, 0 completed",
      })
    ).toBeInTheDocument();
    expect(
      fetchPunchItems.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("keeps the dashboard usable when its Punch Items request fails", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchPunchItems.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Riverside Dashboard" })
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Unable to load Punch Items. Service unavailable"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Schedule" })
    ).toBeEnabled();
    expect(
      screen.getByRole("button", {
        name: "RFI health: 0 open, 0 overdue, 0 closed",
      })
    ).toBeEnabled();
    expect(fetchPunchItems).toHaveBeenCalledTimes(1);
  });

  it("navigates from the dashboard KPI to the Punch List", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    const punchListKpi = await screen.findByRole("button", {
      name: "Punch List health: 0 open, 0 overdue, 0 completed",
    });
    expect(fetchPunchItems).toHaveBeenCalledTimes(1);

    await user.click(punchListKpi);

    expect(
      await screen.findByRole("heading", { name: "Punch List" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/punch-items");
  });

  it("drops a late Punch Items dashboard response after a project switch", async () => {
    let resolveFirstProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchPunchItems.mockImplementation((projectId) => {
      if (projectId === 1) {
        return new Promise((resolve) => {
          resolveFirstProject = resolve;
        });
      }

      return Promise.resolve({
        punch_items: [
          {
            id: 2,
            status: "Verified",
            due_date: "2026-07-01",
          },
        ],
      });
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    await waitFor(() => {
      expect(fetchPunchItems).toHaveBeenCalledWith(1);
    });
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/dashboard");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await waitFor(() => {
      expect(
        fetchPunchItems.mock.calls.map(([projectId]) => projectId)
      ).toEqual([1, 2]);
    });

    await act(async () => {
      resolveFirstProject({
        punch_items: [
          {
            id: 9,
            status: "Open",
            due_date: "2000-01-01",
          },
        ],
      });
    });

    expect(
      screen.getByRole("button", {
        name: "Punch List health: 0 open, 0 overdue, 1 completed",
      })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Punch List health: 1 open, 1 overdue, 0 completed",
      })
    ).not.toBeInTheDocument();
  });

  it("suppresses toast errors for expired-session (401) failures", async () => {
    fetchProjects.mockRejectedValue(new ApiError("Invalid token", 401));

    renderApp();

    // The account looks empty once loading settles; no stale error toast.
    expect(
      await screen.findByText("Welcome to FieldFlow")
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Unable to load projects/)
    ).not.toBeInTheDocument();
  });

  it("surfaces non-auth request failures as error notices", async () => {
    fetchProjects.mockRejectedValue(new ApiError("Server exploded", 500));

    renderApp();

    expect(
      await screen.findByText(/Unable to load projects\. Server exploded/)
    ).toBeInTheDocument();
  });

  it("loads the refresh-safe Change Orders route exactly once", async () => {
    let resolveChangeOrders;

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveChangeOrders = resolve;
        })
    );
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Change Orders" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/change-orders");
    expect(
      screen.getByRole("button", { name: "Change Orders" })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchChangeOrders).toHaveBeenCalledTimes(1);
    });
    expect(fetchChangeOrders).toHaveBeenCalledWith(1);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading change orders..."
    );

    await act(async () => {
      resolveChangeOrders({ change_orders: [] });
    });

    expect(
      await screen.findByText(
        "No change orders yet. Create the first change order above."
      )
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(document.title).toContain("Riverside");
      expect(document.title).toContain("Change Orders | FieldFlow");
    });
  });

  it("validates and creates a title-only Change Order without a number", async () => {
    const user = userEvent.setup();
    const created = makeChangeOrder({
      proposed_amount: "0.00",
      schedule_impact_days: -2,
    });
    let records = [];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockImplementation(async () => ({
      change_orders: records,
    }));
    createChangeOrder.mockImplementation(async () => {
      records = [created];
      return created;
    });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await screen.findByRole("heading", { name: "Change Orders" });
    await user.click(
      screen.getByRole("button", { name: "Create Change Order" })
    );
    expect(
      await screen.findByText("Enter a title or description before saving.")
    ).toBeInTheDocument();
    expect(createChangeOrder).not.toHaveBeenCalled();

    await user.type(
      screen.getByLabelText("Title"),
      "  North entrance revision  "
    );
    await user.type(
      screen.getByLabelText("Company", {
        selector: "#change-order-company",
      }),
      "  Desert Concrete  "
    );
    await user.type(screen.getByLabelText("Proposed amount"), "-1");
    await user.click(
      screen.getByRole("button", { name: "Create Change Order" })
    );
    expect(
      await screen.findByText(/Proposed amount must be a nonnegative value/)
    ).toBeInTheDocument();
    expect(createChangeOrder).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Proposed amount"));
    await user.type(screen.getByLabelText("Proposed amount"), "0");
    await user.type(screen.getByLabelText("Schedule impact"), "-2");
    await user.selectOptions(
      screen.getByLabelText("Status", {
        selector: "#change-order-status",
      }),
      "Draft"
    );
    await user.click(
      screen.getByRole("button", { name: "Create Change Order" })
    );

    expect(createChangeOrder).toHaveBeenCalledWith(1, {
      date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      title: "North entrance revision",
      company: "Desert Concrete",
      status: "Draft",
      description: null,
      reason: null,
      proposed_amount: "0",
      approved_amount: null,
      schedule_impact_days: -2,
      requested_date: null,
      submitted_date: null,
      approved_date: null,
      executed_date: null,
      responsible_party: null,
    });
    expect(
      createChangeOrder.mock.calls[0][1]
    ).not.toHaveProperty("co_number");
    expect(createChangeOrder.mock.calls[0][1]).not.toHaveProperty("amount");
    expect(
      await screen.findByText("Change order created.")
    ).toBeInTheDocument();
    expect(screen.getByText("CO-001")).toBeInTheDocument();
  });

  it("edits a legacy Change Order without submitting its number or amount", async () => {
    const user = userEvent.setup();
    const legacy = makeChangeOrder({
      id: 3,
      co_number: "3",
      title: null,
      amount: "$4,500",
      proposed_amount: null,
      schedule_impact_days: null,
      requested_date: null,
    });
    const updated = {
      ...legacy,
      title: "Legacy revision",
      status: "Void",
      approved_amount: "4000.00",
    };
    let records = [legacy];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockImplementation(async () => ({
      change_orders: records,
    }));
    updateChangeOrder.mockImplementation(async () => {
      records = [updated];
      return updated;
    });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Edit change order 3",
      })
    );
    expect(
      screen.getByRole("heading", { name: "Edit 3" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Change order number")).toHaveValue("3");
    expect(screen.getByLabelText("Change order number")).toHaveAttribute(
      "readonly"
    );

    await user.type(screen.getByLabelText("Title"), "Legacy revision");
    await user.selectOptions(
      screen.getByLabelText("Status", {
        selector: "#change-order-status",
      }),
      "Void"
    );
    await user.type(screen.getByLabelText("Approved amount"), "4000.00");
    await user.click(
      screen.getByRole("button", { name: "Update Change Order" })
    );

    expect(updateChangeOrder).toHaveBeenCalledWith(
      1,
      3,
      expect.objectContaining({
        title: "Legacy revision",
        description: "Revise north entrance.",
        approved_amount: "4000.00",
        status: "Void",
      })
    );
    expect(updateChangeOrder.mock.calls[0][2]).not.toHaveProperty(
      "co_number"
    );
    expect(updateChangeOrder.mock.calls[0][2]).not.toHaveProperty("amount");
    expect(
      await screen.findByText("Change order updated.")
    ).toBeInTheDocument();
  });

  it("validates lifecycle dates against the combined edit state", async () => {
    const user = userEvent.setup();
    const record = makeChangeOrder({
      requested_date: "2026-07-20",
      submitted_date: "2026-07-21",
    });

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockResolvedValue({ change_orders: [record] });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Edit change order CO-001",
      })
    );
    fireEvent.change(screen.getByLabelText("Requested date"), {
      target: { value: "2026-07-22" },
    });
    fireEvent.submit(
      screen
        .getByRole("heading", { name: "Edit CO-001" })
        .closest("form")
    );

    expect(
      await screen.findByText(
        "Submitted date cannot be earlier than requested date."
      )
    ).toBeInTheDocument();
    expect(updateChangeOrder).not.toHaveBeenCalled();
  });

  it("confirms, cancels, and completes Change Order deletion", async () => {
    const user = userEvent.setup();
    let records = [makeChangeOrder()];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockImplementation(async () => ({
      change_orders: records,
    }));
    deleteChangeOrder.mockImplementation(async () => {
      records = [];
      return { message: "Change order deleted" };
    });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Delete change order CO-001",
      })
    );
    expect(
      screen.getByRole("alertdialog", { name: "Delete CO-001?" })
    ).toBeInTheDocument();
    expect(deleteChangeOrder).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(deleteChangeOrder).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", {
        name: "Delete change order CO-001",
      })
    );
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteChangeOrder).toHaveBeenCalledWith(1, 1);
    expect(
      await screen.findByText("Change order deleted.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "No change orders yet. Create the first change order above."
      )
    ).toBeInTheDocument();
  });

  it("reports Change Order load and mutation failures globally", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockRejectedValueOnce(
      new ApiError("Load unavailable", 503)
    );
    window.location.hash = "#/projects/1/change-orders";

    const { unmount } = renderApp();

    expect(
      await screen.findByText(
        "Unable to load change orders. Load unavailable"
      )
    ).toBeInTheDocument();
    unmount();

    vi.clearAllMocks();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchTemplates.mockResolvedValue({ templates: [] });
    fetchTasks.mockResolvedValue({ tasks: [] });
    fetchProjectCompanies.mockResolvedValue({ companies: [] });
    fetchChangeOrders.mockResolvedValue({ change_orders: [] });
    createChangeOrder.mockRejectedValue(
      new ApiError("Save unavailable", 503)
    );

    const user = userEvent.setup();
    renderApp();
    await screen.findByRole("heading", { name: "Change Orders" });
    await user.type(screen.getByLabelText("Description"), "Description only");
    await user.click(
      screen.getByRole("button", { name: "Create Change Order" })
    );

    expect(
      await screen.findByText(
        "Unable to create change order. Save unavailable"
      )
    ).toBeInTheDocument();
  });

  it("reports Change Order update and delete failures globally", async () => {
    const user = userEvent.setup();
    const record = makeChangeOrder();

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchChangeOrders.mockResolvedValue({ change_orders: [record] });
    updateChangeOrder.mockRejectedValue(
      new ApiError("Update unavailable", 503)
    );
    deleteChangeOrder.mockRejectedValue(
      new ApiError("Delete unavailable", 503)
    );
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Edit change order CO-001",
      })
    );
    await user.click(
      screen.getByRole("button", { name: "Update Change Order" })
    );
    expect(
      await screen.findByText(
        "Unable to update change order. Update unavailable"
      )
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel Edit" }));
    await user.click(
      screen.getByRole("button", {
        name: "Delete change order CO-001",
      })
    );
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(
      await screen.findByText(
        "Unable to delete change order. Delete unavailable"
      )
    ).toBeInTheDocument();
    expect(screen.getByText("CO-001")).toBeInTheDocument();
  });

  it("clears Change Order data, edit state, and validation on project switch", async () => {
    const user = userEvent.setup();
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchChangeOrders.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          change_orders: [makeChangeOrder()],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Edit change order CO-001",
      })
    );
    await user.clear(screen.getByLabelText("Title"));
    await user.clear(screen.getByLabelText("Description"));
    await user.click(
      screen.getByRole("button", { name: "Update Change Order" })
    );
    expect(
      await screen.findByText("Enter a title or description before saving.")
    ).toBeInTheDocument();

    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/change-orders");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    expect(
      await screen.findByRole("heading", { name: "Create Change Order" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("");
    expect(screen.getByLabelText("Description")).toHaveValue("");
    expect(screen.getByLabelText("Change order number")).toHaveValue(
      "Assigned when saved"
    );
    expect(screen.queryByText("CO-001")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Enter a title or description before saving.")
    ).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading change orders..."
    );

    await act(async () => {
      resolveSecondProject({ change_orders: [] });
    });

    expect(
      await screen.findByText(
        "No change orders yet. Create the first change order above."
      )
    ).toBeInTheDocument();
    expect(
      fetchChangeOrders.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("rejects a stale Change Orders response after a project switch", async () => {
    let resolveFirstProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchChangeOrders.mockImplementation((projectId) => {
      if (projectId === 1) {
        return new Promise((resolve) => {
          resolveFirstProject = resolve;
        });
      }

      return Promise.resolve({
        change_orders: [
          makeChangeOrder({
            id: 2,
            project_id: 2,
            co_number: "CO-002",
            title: "North Ridge change",
          }),
        ],
      });
    });
    window.location.hash = "#/projects/1/change-orders";

    renderApp();

    await screen.findByRole("heading", { name: "Change Orders" });
    await waitFor(() => {
      expect(fetchChangeOrders).toHaveBeenCalledWith(1);
    });

    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/change-orders");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    expect(await screen.findByText("CO-002")).toBeInTheDocument();

    await act(async () => {
      resolveFirstProject({
        change_orders: [
          makeChangeOrder({ title: "Stale Riverside change" }),
        ],
      });
    });

    expect(screen.queryByText("Stale Riverside change")).not.toBeInTheDocument();
    expect(screen.getByText("North Ridge change")).toBeInTheDocument();
    expect(
      fetchChangeOrders.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("navigates to the selected project's RFI route and loads RFIs", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    await screen.findByText("Riverside Dashboard");
    await user.click(screen.getByRole("button", { name: "RFIs" }));

    expect(
      await screen.findByRole("heading", {
        name: "Requests for Information",
      })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/rfis");
    expect(fetchRFIs).toHaveBeenCalledWith(1);
    expect(
      screen.getByText("No RFIs yet. Create the first RFI above.")
    ).toBeInTheDocument();
  });

  it("validates and creates an RFI with trimmed ISO-string fields", async () => {
    const user = userEvent.setup();
    const createdRFI = {
      id: 1,
      project_id: 1,
      number: "RFI-001",
      subject: "Door frame detail",
      question: "Which detail applies?",
      responsible_company: "Desert Glass",
      submitted_date: "2026-07-25",
      due_date: "2026-07-30",
      response: null,
      status: "Open",
      created_at: "2026-07-25T12:00:00Z",
      updated_at: "2026-07-25T12:00:00Z",
    };
    let records = [];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchRFIs.mockImplementation(async () => ({ rfis: records }));
    createRFI.mockImplementation(async () => {
      records = [createdRFI];
      return createdRFI;
    });
    window.location.hash = "#/projects/1/rfis";

    renderApp();

    await screen.findByRole("heading", {
      name: "Requests for Information",
    });
    await user.type(screen.getByLabelText("Subject *"), "   ");
    await user.type(
      screen.getByLabelText("Question *"),
      "Which detail applies?"
    );
    await user.click(screen.getByRole("button", { name: "Create RFI" }));

    expect(
      await screen.findByText(
        "Complete the subject, question, and submitted date before saving."
      )
    ).toBeInTheDocument();
    expect(createRFI).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Subject *"));
    await user.type(screen.getByLabelText("Subject *"), "  Door frame detail  ");
    await user.type(
      screen.getByLabelText("Responsible company"),
      "  Desert Glass  "
    );
    await user.type(screen.getByLabelText("Due date"), "2000-01-01");
    fireEvent.submit(
      screen.getByRole("heading", { name: "Create RFI" }).closest("form")
    );

    expect(
      await screen.findByText(
        "Due date cannot be earlier than submitted date."
      )
    ).toBeInTheDocument();
    expect(createRFI).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Due date"));
    await user.type(screen.getByLabelText("Due date"), "2099-12-31");
    await user.click(screen.getByRole("button", { name: "Create RFI" }));

    expect(createRFI).toHaveBeenCalledWith(1, {
      subject: "Door frame detail",
      question: "Which detail applies?",
      responsible_company: "Desert Glass",
      submitted_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      due_date: "2099-12-31",
      response: null,
      status: "Open",
    });
    expect(await screen.findByText("RFI-001")).toBeInTheDocument();
    expect(screen.getByText("RFI created.")).toBeInTheDocument();
  });

  it("edits and closes an RFI with a response", async () => {
    const user = userEvent.setup();
    const openRFI = {
      id: 7,
      project_id: 1,
      number: "RFI-007",
      subject: "Confirm finish",
      question: "Which finish applies?",
      responsible_company: "Desert Glass",
      submitted_date: "2026-07-20",
      due_date: "2026-07-28",
      response: null,
      status: "Open",
    };
    const closedRFI = {
      ...openRFI,
      response: "Use dark bronze.",
      status: "Closed",
    };
    let records = [openRFI];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchRFIs.mockImplementation(async () => ({ rfis: records }));
    updateRFI.mockImplementation(async () => {
      records = [closedRFI];
      return closedRFI;
    });
    window.location.hash = "#/projects/1/rfis";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Edit RFI-007" })
    );

    expect(
      screen.getByRole("heading", { name: "Edit RFI-007" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Subject *")).toHaveValue("Confirm finish");

    await user.selectOptions(screen.getByLabelText("Status"), "Closed");
    await user.type(screen.getByLabelText("Response"), "Use dark bronze.");
    await user.click(screen.getByRole("button", { name: "Update RFI" }));

    expect(updateRFI).toHaveBeenCalledWith(
      1,
      7,
      expect.objectContaining({
        subject: "Confirm finish",
        response: "Use dark bronze.",
        status: "Closed",
      })
    );
    expect(await screen.findByText("RFI updated.")).toBeInTheDocument();
    expect(screen.getByText("Use dark bronze.")).toBeInTheDocument();
  });

  it("deletes an RFI through the confirmation workflow", async () => {
    const user = userEvent.setup();
    const rfi = {
      id: 3,
      project_id: 1,
      number: "RFI-003",
      subject: "Confirm hardware",
      question: "Which set applies?",
      responsible_company: null,
      submitted_date: "2026-07-20",
      due_date: null,
      response: null,
      status: "Pending",
    };
    let records = [rfi];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchRFIs.mockImplementation(async () => ({ rfis: records }));
    deleteRFI.mockImplementation(async () => {
      records = [];
      return { message: "RFI deleted" };
    });
    window.location.hash = "#/projects/1/rfis";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Delete RFI-003" })
    );

    expect(
      screen.getByRole("alertdialog", { name: "Delete RFI-003?" })
    ).toBeInTheDocument();
    expect(deleteRFI).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteRFI).toHaveBeenCalledWith(1, 3);
    expect(await screen.findByText("RFI deleted.")).toBeInTheDocument();
    expect(
      screen.getByText("No RFIs yet. Create the first RFI above.")
    ).toBeInTheDocument();
  });

  it("announces RFI request failures through the existing feedback banner", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    createRFI.mockRejectedValue(new ApiError("Service unavailable", 503));
    window.location.hash = "#/projects/1/rfis";

    renderApp();

    await screen.findByRole("heading", {
      name: "Requests for Information",
    });
    await user.type(screen.getByLabelText("Subject *"), "Door frame detail");
    await user.type(
      screen.getByLabelText("Question *"),
      "Which detail applies?"
    );
    await user.click(screen.getByRole("button", { name: "Create RFI" }));

    expect(
      await screen.findByText(
        "Unable to create RFI. Service unavailable"
      )
    ).toBeInTheDocument();
  });

  it("announces failures while loading the selected project's RFIs", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchRFIs.mockRejectedValue(new ApiError("Service unavailable", 503));
    window.location.hash = "#/projects/1/rfis";

    renderApp();

    expect(
      await screen.findByText("Unable to load RFIs. Service unavailable")
    ).toBeInTheDocument();
  });

  it("loads the selected project's refresh-safe Submittals route once", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Submittals" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/submittals");
    await waitFor(() => {
      expect(document.title).toContain("Riverside");
      expect(document.title).toContain("Submittals | FieldFlow");
    });
    await waitFor(() => {
      expect(fetchSubmittals).toHaveBeenCalledTimes(1);
    });
    expect(fetchSubmittals).toHaveBeenCalledWith(1);
    expect(
      screen.getByText(
        "No submittals yet. Create the first submittal above."
      )
    ).toBeInTheDocument();
  });

  it("validates and creates a Draft Submittal without a submitted date", async () => {
    const user = userEvent.setup();
    const createdSubmittal = {
      id: 1,
      project_id: 1,
      number: "SUB-001",
      specification_section: "08 41 13",
      title: "Aluminum-framed entrances",
      responsible_company: "Desert Glass",
      submitted_date: null,
      required_by_date: null,
      reviewed_date: null,
      status: "Draft",
      reviewer: null,
      remarks: null,
      created_at: "2026-07-25T12:00:00Z",
      updated_at: "2026-07-25T12:00:00Z",
    };
    let records = [];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchSubmittals.mockImplementation(async () => ({
      submittals: records,
    }));
    createSubmittal.mockImplementation(async () => {
      records = [createdSubmittal];
      return createdSubmittal;
    });
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    await screen.findByRole("heading", { name: "Submittals" });
    await user.type(screen.getByLabelText("Specification section *"), "   ");
    await user.type(
      screen.getByLabelText("Title *"),
      "Aluminum-framed entrances"
    );
    await user.click(
      screen.getByRole("button", { name: "Create Submittal" })
    );

    expect(
      await screen.findByText(
        "Complete the specification section and title before saving."
      )
    ).toBeInTheDocument();
    expect(createSubmittal).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Specification section *"));
    await user.type(
      screen.getByLabelText("Specification section *"),
      "  08 41 13  "
    );
    await user.type(
      screen.getByLabelText("Responsible company"),
      "  Desert Glass  "
    );
    await user.type(screen.getByLabelText("Submitted date"), "2026-07-25");
    await user.type(screen.getByLabelText("Required-by date"), "2026-07-24");
    fireEvent.submit(
      screen
        .getByRole("heading", { name: "Create Submittal" })
        .closest("form")
    );

    expect(
      await screen.findByText(
        "Required-by date cannot be earlier than submitted date."
      )
    ).toBeInTheDocument();
    expect(createSubmittal).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Required-by date"));
    await user.type(screen.getByLabelText("Reviewed date"), "2026-07-24");
    fireEvent.submit(
      screen
        .getByRole("heading", { name: "Create Submittal" })
        .closest("form")
    );

    expect(
      await screen.findByText(
        "Reviewed date cannot be earlier than submitted date."
      )
    ).toBeInTheDocument();
    expect(createSubmittal).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Submitted date"));
    await user.clear(screen.getByLabelText("Reviewed date"));
    await user.click(
      screen.getByRole("button", { name: "Create Submittal" })
    );

    expect(createSubmittal).toHaveBeenCalledWith(1, {
      specification_section: "08 41 13",
      title: "Aluminum-framed entrances",
      responsible_company: "Desert Glass",
      submitted_date: null,
      required_by_date: null,
      reviewed_date: null,
      status: "Draft",
      reviewer: null,
      remarks: null,
    });
    expect(await screen.findByText("SUB-001")).toBeInTheDocument();
    expect(screen.getByText("Submittal created.")).toBeInTheDocument();
  });

  it("edits a Submittal and supports the complete status workflow", async () => {
    const user = userEvent.setup();
    const submitted = {
      id: 7,
      project_id: 1,
      number: "SUB-007",
      specification_section: "08 41 13",
      title: "Storefront package",
      responsible_company: "Desert Glass",
      submitted_date: "2026-07-20",
      required_by_date: "2026-07-30",
      reviewed_date: null,
      status: "Under Review",
      reviewer: "Project Architect",
      remarks: "Initial package",
    };
    const revised = {
      ...submitted,
      status: "Revise and Resubmit",
      reviewed_date: "2026-07-25",
      remarks: "Revise anchorage details.",
    };
    let records = [submitted];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchSubmittals.mockImplementation(async () => ({
      submittals: records,
    }));
    updateSubmittal.mockImplementation(async () => {
      records = [revised];
      return revised;
    });
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Edit SUB-007" })
    );

    expect(
      screen.getByRole("heading", { name: "Edit SUB-007" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Title *")).toHaveValue(
      "Storefront package"
    );
    expect(screen.getByLabelText("Reviewer")).toHaveValue(
      "Project Architect"
    );

    await user.selectOptions(
      screen.getByLabelText("Status"),
      "Revise and Resubmit"
    );
    await user.type(screen.getByLabelText("Reviewed date"), "2026-07-25");
    await user.clear(screen.getByLabelText("Remarks"));
    await user.type(
      screen.getByLabelText("Remarks"),
      "  Revise anchorage details.  "
    );
    await user.click(
      screen.getByRole("button", { name: "Update Submittal" })
    );

    expect(updateSubmittal).toHaveBeenCalledWith(
      1,
      7,
      expect.objectContaining({
        specification_section: "08 41 13",
        title: "Storefront package",
        reviewed_date: "2026-07-25",
        status: "Revise and Resubmit",
        remarks: "Revise anchorage details.",
      })
    );
    expect(await screen.findByText("Submittal updated.")).toBeInTheDocument();
    expect(screen.getByText("Revise anchorage details.")).toBeInTheDocument();
  });

  it("deletes a Submittal through the confirmation workflow", async () => {
    const user = userEvent.setup();
    const submittal = {
      id: 3,
      project_id: 1,
      number: "SUB-003",
      specification_section: "09 29 00",
      title: "Gypsum board package",
      responsible_company: null,
      submitted_date: null,
      required_by_date: null,
      reviewed_date: null,
      status: "Draft",
      reviewer: null,
      remarks: null,
    };
    let records = [submittal];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchSubmittals.mockImplementation(async () => ({
      submittals: records,
    }));
    deleteSubmittal.mockImplementation(async () => {
      records = [];
      return { message: "Submittal deleted" };
    });
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Delete SUB-003" })
    );

    expect(
      screen.getByRole("alertdialog", { name: "Delete SUB-003?" })
    ).toBeInTheDocument();
    expect(deleteSubmittal).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteSubmittal).toHaveBeenCalledWith(1, 3);
    expect(await screen.findByText("Submittal deleted.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No submittals yet. Create the first submittal above."
      )
    ).toBeInTheDocument();
  });

  it("announces failures while loading the selected project's Submittals", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchSubmittals.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    expect(
      await screen.findByText(
        "Unable to load Submittals. Service unavailable"
      )
    ).toBeInTheDocument();
  });

  it("announces Submittal mutation failures through the feedback banner", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    createSubmittal.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    await screen.findByRole("heading", { name: "Submittals" });
    await user.type(
      screen.getByLabelText("Specification section *"),
      "08 41 13"
    );
    await user.type(
      screen.getByLabelText("Title *"),
      "Aluminum-framed entrances"
    );
    await user.click(
      screen.getByRole("button", { name: "Create Submittal" })
    );

    expect(
      await screen.findByText(
        "Unable to create Submittal. Service unavailable"
      )
    ).toBeInTheDocument();
  });

  it("clears Submittals while switching projects and drops stale data", async () => {
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchSubmittals.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          submittals: [
            {
              id: 1,
              project_id: 1,
              number: "SUB-001",
              specification_section: "08 41 13",
              title: "Storefront package",
              responsible_company: null,
              submitted_date: null,
              required_by_date: null,
              reviewed_date: null,
              status: "Draft",
              reviewer: null,
              remarks: null,
            },
          ],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });
    window.location.hash = "#/projects/1/submittals";

    renderApp();

    expect(await screen.findByText("SUB-001")).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/submittals");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await waitFor(() => {
      expect(screen.queryByText("SUB-001")).not.toBeInTheDocument();
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Loading Submittals..."
    );

    await act(async () => {
      resolveSecondProject({ submittals: [] });
    });

    expect(
      await screen.findByText(
        "No submittals yet. Create the first submittal above."
      )
    ).toBeInTheDocument();
    expect(
      fetchSubmittals.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("navigates to a refresh-safe Punch List route with one request", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    const punchListLink = await screen.findByRole("button", {
      name: "Punch List",
    });
    await screen.findByRole("button", {
      name: "Punch List health: 0 open, 0 overdue, 0 completed",
    });
    expect(fetchPunchItems).toHaveBeenCalledTimes(1);
    fetchPunchItems.mockClear();

    await user.click(punchListLink);

    expect(
      await screen.findByRole("heading", { name: "Punch List" })
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects/1/punch-items");
    expect(document.title).toContain("Riverside");
    expect(document.title).toContain("Punch List | FieldFlow");
    await waitFor(() => {
      expect(fetchPunchItems).toHaveBeenCalledTimes(1);
    });
    expect(fetchPunchItems).toHaveBeenCalledWith(1);
    expect(
      screen.getByText(
        "No punch items yet. Create the first punch item above."
      )
    ).toBeInTheDocument();
  });

  it("validates and creates a Punch Item with normalized values", async () => {
    const user = userEvent.setup();
    const createdPunchItem = {
      id: 1,
      project_id: 1,
      number: "PUNCH-001",
      location: "Level 2 - Corridor",
      trade: "Drywall",
      description: "Patch damaged gypsum board",
      responsible_company: "Desert Drywall",
      assigned_to: "A. Rivera",
      priority: "Critical",
      status: "In Progress",
      due_date: "2026-07-25",
      completed_date: "2026-07-26",
    };
    let records = [];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchPunchItems.mockImplementation(async () => ({
      punch_items: records,
    }));
    createPunchItem.mockImplementation(async () => {
      records = [createdPunchItem];
      return createdPunchItem;
    });
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    await screen.findByRole("heading", { name: "Punch List" });
    await user.type(screen.getByLabelText("Location *"), "   ");
    await user.type(
      screen.getByLabelText("Description *"),
      "Patch damaged gypsum board"
    );
    await user.click(
      screen.getByRole("button", { name: "Create Punch Item" })
    );

    expect(
      await screen.findByText(
        "Complete the location and description before saving."
      )
    ).toBeInTheDocument();
    expect(createPunchItem).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Location *"));
    await user.type(
      screen.getByLabelText("Location *"),
      "  Level 2 - Corridor  "
    );
    await user.clear(screen.getByLabelText("Description *"));
    await user.type(screen.getByLabelText("Description *"), "   ");
    await user.click(
      screen.getByRole("button", { name: "Create Punch Item" })
    );

    expect(createPunchItem).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Description *"));
    await user.type(
      screen.getByLabelText("Description *"),
      "  Patch damaged gypsum board  "
    );
    await user.type(screen.getByLabelText("Trade"), "  Drywall  ");
    await user.type(
      screen.getByLabelText("Responsible company"),
      "  Desert Drywall  "
    );
    await user.type(screen.getByLabelText("Assigned to"), "  A. Rivera  ");
    await user.selectOptions(screen.getByLabelText("Priority"), "Critical");
    await user.selectOptions(
      screen.getByLabelText("Status"),
      "In Progress"
    );
    await user.type(screen.getByLabelText("Due date"), "2026-07-25");
    await user.type(screen.getByLabelText("Completed date"), "2026-07-24");
    fireEvent.submit(
      screen
        .getByRole("heading", { name: "Create Punch Item" })
        .closest("form")
    );

    expect(
      await screen.findByText(
        "Completed date cannot be earlier than due date."
      )
    ).toBeInTheDocument();
    expect(createPunchItem).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Completed date"));
    await user.type(screen.getByLabelText("Completed date"), "2026-07-26");
    await user.click(
      screen.getByRole("button", { name: "Create Punch Item" })
    );

    expect(createPunchItem).toHaveBeenCalledWith(1, {
      location: "Level 2 - Corridor",
      trade: "Drywall",
      description: "Patch damaged gypsum board",
      responsible_company: "Desert Drywall",
      assigned_to: "A. Rivera",
      priority: "Critical",
      status: "In Progress",
      due_date: "2026-07-25",
      completed_date: "2026-07-26",
    });
    expect(await screen.findByText("PUNCH-001")).toBeInTheDocument();
    expect(screen.getByText("Punch Item created.")).toBeInTheDocument();
  });

  it("edits a Punch Item priority and status", async () => {
    const user = userEvent.setup();
    const openItem = {
      id: 7,
      project_id: 1,
      number: "PUNCH-007",
      location: "Level 1 Lobby",
      trade: "Electrical",
      description: "Align device cover",
      responsible_company: "Desert Electric",
      assigned_to: "M. Chen",
      priority: "Medium",
      status: "Open",
      due_date: "2026-07-30",
      completed_date: null,
    };
    const verifiedItem = {
      ...openItem,
      priority: "High",
      status: "Verified",
      completed_date: "2026-07-30",
    };
    let records = [openItem];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchPunchItems.mockImplementation(async () => ({
      punch_items: records,
    }));
    updatePunchItem.mockImplementation(async () => {
      records = [verifiedItem];
      return verifiedItem;
    });
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Edit PUNCH-007" })
    );

    expect(
      screen.getByRole("heading", { name: "Edit PUNCH-007" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Location *")).toHaveValue(
      "Level 1 Lobby"
    );
    expect(screen.getByLabelText("Assigned to")).toHaveValue("M. Chen");

    await user.selectOptions(screen.getByLabelText("Priority"), "High");
    await user.selectOptions(screen.getByLabelText("Status"), "Verified");
    await user.type(screen.getByLabelText("Completed date"), "2026-07-30");
    await user.click(
      screen.getByRole("button", { name: "Update Punch Item" })
    );

    expect(updatePunchItem).toHaveBeenCalledWith(
      1,
      7,
      expect.objectContaining({
        priority: "High",
        status: "Verified",
        completed_date: "2026-07-30",
      })
    );
    expect(await screen.findByText("Punch Item updated.")).toBeInTheDocument();
  });

  it("deletes a Punch Item through the confirmation workflow", async () => {
    const user = userEvent.setup();
    const punchItem = {
      id: 3,
      project_id: 1,
      number: "PUNCH-003",
      location: "Roof",
      trade: null,
      description: "Remove temporary protection",
      responsible_company: null,
      assigned_to: null,
      priority: "Low",
      status: "Open",
      due_date: null,
      completed_date: null,
    };
    let records = [punchItem];

    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchPunchItems.mockImplementation(async () => ({
      punch_items: records,
    }));
    deletePunchItem.mockImplementation(async () => {
      records = [];
      return { message: "Punch Item deleted" };
    });
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Delete PUNCH-003" })
    );

    expect(
      screen.getByRole("alertdialog", { name: "Delete PUNCH-003?" })
    ).toBeInTheDocument();
    expect(deletePunchItem).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deletePunchItem).toHaveBeenCalledWith(1, 3);
    expect(await screen.findByText("Punch Item deleted.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No punch items yet. Create the first punch item above."
      )
    ).toBeInTheDocument();
  });

  it("announces failures while loading the selected project's Punch Items", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchPunchItems.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    expect(
      await screen.findByText(
        "Unable to load Punch Items. Service unavailable"
      )
    ).toBeInTheDocument();
  });

  it("announces Punch Item mutation failures through the feedback banner", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    createPunchItem.mockRejectedValue(
      new ApiError("Service unavailable", 503)
    );
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    await screen.findByRole("heading", { name: "Punch List" });
    await user.type(screen.getByLabelText("Location *"), "Level 1 Lobby");
    await user.type(
      screen.getByLabelText("Description *"),
      "Align device cover"
    );
    await user.click(
      screen.getByRole("button", { name: "Create Punch Item" })
    );

    expect(
      await screen.findByText(
        "Unable to create Punch Item. Service unavailable"
      )
    ).toBeInTheDocument();
  });

  it("clears Punch Items while switching projects", async () => {
    let resolveSecondProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchPunchItems.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          punch_items: [
            {
              id: 1,
              project_id: 1,
              number: "PUNCH-001",
              location: "Riverside Lobby",
              trade: null,
              description: "First project item",
              responsible_company: null,
              assigned_to: null,
              priority: "Medium",
              status: "Open",
              due_date: null,
              completed_date: null,
            },
          ],
        });
      }

      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    expect(await screen.findByText("PUNCH-001")).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/punch-items");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await waitFor(() => {
      expect(screen.queryByText("PUNCH-001")).not.toBeInTheDocument();
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Loading Punch Items..."
    );

    await act(async () => {
      resolveSecondProject({
        punch_items: [
          {
            id: 2,
            project_id: 2,
            number: "PUNCH-002",
            location: "North Ridge Roof",
            trade: null,
            description: "Second project item",
            responsible_company: null,
            assigned_to: null,
            priority: "High",
            status: "In Progress",
            due_date: null,
            completed_date: null,
          },
        ],
      });
    });

    expect(await screen.findByText("PUNCH-002")).toBeInTheDocument();
    expect(
      fetchPunchItems.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("drops a late Punch Items response after a project switch", async () => {
    let resolveFirstProject;

    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchPunchItems.mockImplementation((projectId) => {
      if (projectId === 1) {
        return new Promise((resolve) => {
          resolveFirstProject = resolve;
        });
      }

      return Promise.resolve({
        punch_items: [
          {
            id: 2,
            project_id: 2,
            number: "PUNCH-002",
            location: "North Ridge Roof",
            trade: null,
            description: "Second project item",
            responsible_company: null,
            assigned_to: null,
            priority: "High",
            status: "In Progress",
            due_date: null,
            completed_date: null,
          },
        ],
      });
    });
    window.location.hash = "#/projects/1/punch-items";

    renderApp();

    await waitFor(() => {
      expect(fetchPunchItems).toHaveBeenCalledWith(1);
    });
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/punch-items");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    expect(await screen.findByText("PUNCH-002")).toBeInTheDocument();

    await act(async () => {
      resolveFirstProject({
        punch_items: [
          {
            id: 9,
            project_id: 1,
            number: "PUNCH-009",
            location: "Stale location",
            trade: null,
            description: "Late first project response",
            responsible_company: null,
            assigned_to: null,
            priority: "Critical",
            status: "Open",
            due_date: null,
            completed_date: null,
          },
        ],
      });
    });

    expect(screen.getByText("PUNCH-002")).toBeInTheDocument();
    expect(screen.queryByText("PUNCH-009")).not.toBeInTheDocument();
    expect(
      fetchPunchItems.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });
});
