import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./services/api", () => ({
  fetchProjects: vi.fn(),
  fetchProjectDashboard: vi.fn(),
  createProject: vi.fn(),
  fetchTasks: vi.fn(),
  fetchScheduleSettings: vi.fn(),
  updateScheduleSettings: vi.fn(),
  listScheduleBaselines: vi.fn(),
  createScheduleBaseline: vi.fn(),
  getScheduleBaseline: vi.fn(),
  archiveScheduleBaseline: vi.fn(),
  selectScheduleBaseline: vi.fn(),
  fetchScheduleVariance: vi.fn(),
  listLookAheadPlans: vi.fn(),
  createLookAheadPlan: vi.fn(),
  getLookAheadPlan: vi.fn(),
  updateLookAheadPlan: vi.fn(),
  archiveLookAheadPlan: vi.fn(),
  updateLookAheadItem: vi.fn(),
  createTask: vi.fn(),
  deleteTask: vi.fn(),
  updateTask: vi.fn(),
  updateTaskProgress: vi.fn(),
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
  listAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  downloadAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
  listRelationships: vi.fn(),
  createRelationship: vi.fn(),
  deleteRelationship: vi.fn(),
  listRelationshipCandidates: vi.fn(),
  exploreDocuments: vi.fn(),
  listFolderTree: vi.fn(),
  listRecentDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  downloadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  getDocumentExtraction: vi.fn(),
  reprocessDocumentExtraction: vi.fn(),
  searchProjectDocuments: vi.fn(),
  createFolder: vi.fn(),
  listDrawingSets: vi.fn(),
  createDrawingSet: vi.fn(),
  updateDrawingSet: vi.fn(),
  archiveDrawingSet: vi.fn(),
  getDrawingRegister: vi.fn(),
  listDrawingSetSheets: vi.fn(),
  createDrawingSheet: vi.fn(),
  updateDrawingSheet: vi.fn(),
  archiveDrawingSheet: vi.fn(),
  listDrawingRevisions: vi.fn(),
  uploadDrawingRevision: vi.fn(),
  downloadDrawingRevision: vi.fn(),
  listDrawingIssues: vi.fn(),
  createDrawingIssue: vi.fn(),
  updateDrawingIssue: vi.fn(),
  deleteDrawingIssue: vi.fn(),
  addDrawingIssueRevision: vi.fn(),
  removeDrawingIssueRevision: vi.fn(),
  issueDrawingIssue: vi.fn(),
  voidDrawingIssue: vi.fn(),
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
  fetchProjectDashboard,
  fetchProjects,
  fetchRFIs,
  fetchScheduleVariance,
  fetchScheduleSettings,
  fetchSubmittals,
  fetchTasks,
  fetchTemplates,
  exploreDocuments,
  listFolderTree,
  listRecentDocuments,
  listAttachments,
  listScheduleBaselines,
  listLookAheadPlans,
  searchProjectDocuments,
  getDrawingRegister,
  listDrawingIssues,
  listDrawingSets,
  listDrawingSetSheets,
  updateRFI,
  updateScheduleSettings,
  updateTaskProgress,
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

function makeDashboard(projectId = 1, projectName = "Riverside", overrides = {}) {
  return {
    as_of: "2026-07-27",
    generated_at: "2026-07-27T23:00:00Z",
    project: { id: projectId, name: projectName },
    schedule: {
      task_count: 0,
      planned_start: null,
      planned_finish: null,
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
      total: 0,
      active: 0,
      approved: 0,
      rejected: 0,
      unknown_status: 0,
      active_value: "0.00",
      approved_value: "0.00",
    },
    daily_logs: {
      total: 0,
      latest_log_date: null,
      today_count: 0,
      today_manpower: 0,
      last_7_days_count: 0,
    },
    documents: {
      total: 0,
      uploaded_last_7_days: 0,
      recent: [],
    },
    attention_items: [],
    upcoming_tasks: [],
    recent_updates: [],
    ...overrides,
  };
}

describe("App integration (hooks wiring)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.location.hash = "";
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              url.endsWith("/auth/csrf")
                ? { csrf_token: "integration-csrf" }
                : {
                    access_token: "integration-token",
                    token_type: "bearer",
                    csrf_token: "integration-csrf",
                    user: { id: 1, email: "pm@example.com" },
                  }
            ),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            }
          )
        )
      )
    );

    fetchProjects.mockResolvedValue({ projects: [] });
    fetchProjectDashboard.mockResolvedValue(makeDashboard());
    fetchTemplates.mockResolvedValue({ templates: [] });
    fetchTasks.mockResolvedValue({ tasks: [] });
    fetchScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-06-22",
      data_date: "2026-06-22",
      comparison_baseline_id: null,
      created_at: "2026-06-22T00:00:00Z",
      updated_at: "2026-06-22T00:00:00Z",
    });
    updateScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-06-22",
      data_date: "2026-06-22",
      comparison_baseline_id: null,
      created_at: "2026-06-22T00:00:00Z",
      updated_at: "2026-06-22T00:00:00Z",
    });
    listScheduleBaselines.mockResolvedValue({
      baselines: [],
      comparison_baseline_id: null,
      total: 0,
      limit: 100,
      offset: 0,
    });
    listLookAheadPlans.mockResolvedValue({
      plans: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    fetchScheduleVariance.mockResolvedValue({
      baseline: null,
      summary: null,
      tasks: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
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
    exploreDocuments.mockResolvedValue({
      project_id: 1,
      current_folder: null,
      breadcrumbs: [],
      folders: [],
      documents: [],
      pagination: {
        limit: 50,
        offset: 0,
        total: 0,
        has_more: false,
      },
    });
    listFolderTree.mockResolvedValue({ folders: [] });
    listRecentDocuments.mockResolvedValue({ documents: [] });
    listDrawingSets.mockResolvedValue({ drawing_sets: [] });
    getDrawingRegister.mockResolvedValue({
      project_id: 1,
      sheets: [],
      pagination: {
        limit: 50,
        offset: 0,
        total: 0,
        has_more: false,
      },
    });
    listDrawingSetSheets.mockResolvedValue({ sheets: [] });
    listDrawingIssues.mockResolvedValue({ issues: [] });
    createPunchItem.mockResolvedValue({});
    updatePunchItem.mockResolvedValue({});
    deletePunchItem.mockResolvedValue({ message: "Punch Item deleted" });
    listAttachments.mockResolvedValue({ attachments: [] });
  });

  it("shows the login experience when unauthenticated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              url.endsWith("/auth/csrf")
                ? { csrf_token: "integration-csrf" }
                : { detail: "Invalid authentication credentials" }
            ),
            {
              status: url.endsWith("/auth/csrf") ? 200 : 401,
              headers: { "Content-Type": "application/json" },
            }
          )
        )
      )
    );

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Welcome back" })
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

  it("loads one aggregate request and no dashboard collections", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchProjectDashboard.mockResolvedValue(
      makeDashboard(1, "Riverside", {
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
      })
    );

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");

    expect(
      await screen.findByRole("heading", { name: "Project Dashboard" })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchProjectDashboard).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText("Clarify storefront flashing")).toBeInTheDocument();
    expect(screen.getByText("Install storefront")).toBeInTheDocument();
    expect(
      screen.getByText("Recently clarified storefront flashing")
    ).toBeInTheDocument();
    expect(fetchProjectDashboard).toHaveBeenCalledWith(
      1,
      expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(fetchTasks).not.toHaveBeenCalled();
    expect(fetchProjectCompanies).not.toHaveBeenCalled();
    expect(fetchDailyLogs).not.toHaveBeenCalled();
    expect(fetchInspections).not.toHaveBeenCalled();
    expect(fetchNotesDelays).not.toHaveBeenCalled();
    expect(fetchChangeOrders).not.toHaveBeenCalled();
    expect(fetchRFIs).not.toHaveBeenCalled();
    expect(fetchSubmittals).not.toHaveBeenCalled();
    expect(fetchPunchItems).not.toHaveBeenCalled();
    expect(listAttachments).not.toHaveBeenCalled();
    expect(listLookAheadPlans).not.toHaveBeenCalled();
  });

  it("loads project documents only from the selected project settings", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    await screen.findByRole("heading", { name: "Project Dashboard" });
    expect(listAttachments).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Project Settings" })
    );

    expect(
      await screen.findByRole("heading", { name: "Project Documents" })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(listAttachments).toHaveBeenCalledTimes(1);
    });
  });

  it("routes to the project document explorer without loading attachment panels", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    await screen.findByRole("heading", { name: "Project Dashboard" });
    await user.click(screen.getByRole("button", { name: "Documents" }));

    expect(window.location.hash).toBe("#/projects/1/documents");
    expect(
      await screen.findByRole("heading", {
        name: "Project Documents",
        level: 1,
      })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(exploreDocuments).toHaveBeenCalledTimes(1);
      expect(listFolderTree).toHaveBeenCalledTimes(1);
      expect(listRecentDocuments).toHaveBeenCalledTimes(1);
    });
    expect(listAttachments).not.toHaveBeenCalled();
  });

  it("lazy-routes to document search without issuing an initial search", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    await screen.findByRole("heading", { name: "Project Dashboard" });
    await user.click(
      screen.getByRole("button", { name: "Document Search" })
    );

    expect(window.location.hash).toBe("#/projects/1/search");
    expect(
      await screen.findByRole("heading", {
        name: "Document Search",
        level: 1,
      })
    ).toBeInTheDocument();
    expect(searchProjectDocuments).not.toHaveBeenCalled();
    expect(exploreDocuments).not.toHaveBeenCalled();
    expect(listAttachments).not.toHaveBeenCalled();
  });

  it("routes to project drawings with one bounded register request", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });

    renderApp();

    await screen.findByRole("option", { name: "Riverside" });
    await user.selectOptions(screen.getByLabelText("Project"), "1");
    await screen.findByRole("heading", { name: "Project Dashboard" });
    await user.click(screen.getByRole("button", { name: "Drawings" }));

    expect(window.location.hash).toBe("#/projects/1/drawings");
    expect(
      await screen.findByRole("heading", {
        name: "Drawing Register",
        level: 1,
      })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(listDrawingSets).toHaveBeenCalledTimes(1);
      expect(getDrawingRegister).toHaveBeenCalledTimes(1);
    });
    expect(listAttachments).not.toHaveBeenCalled();
    expect(exploreDocuments).not.toHaveBeenCalled();
  });

  it("clears dashboard data, aborts the old request, and rejects stale results", async () => {
    const first = {};
    const second = {};
    first.promise = new Promise((resolve) => {
      first.resolve = resolve;
    });
    second.promise = new Promise((resolve) => {
      second.resolve = resolve;
    });
    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchProjectDashboard
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    await waitFor(() =>
      expect(fetchProjectDashboard).toHaveBeenCalledTimes(1)
    );
    const firstSignal = fetchProjectDashboard.mock.calls[0][2].signal;

    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/dashboard");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    expect(firstSignal.aborted).toBe(true);
    expect(
      await screen.findByText("Loading project summary…")
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Open RFIs: 5")).not.toBeInTheDocument();

    await act(async () => {
      second.resolve(
        makeDashboard(2, "North Ridge", {
          rfis: { total: 1, open: 1, overdue: 0, due_soon: 0 },
          attention_items: [
            {
              resource_type: "rfi",
              record_id: 2,
              identifier: "RFI-002",
              title: "North Ridge question",
              due_date: "2026-07-25",
              reason: "Overdue",
              severity: "overdue",
              target_page: "rfis",
            },
          ],
          upcoming_tasks: [
            {
              id: 22,
              name: "North Ridge mobilization",
              start_date: "2026-07-29",
              end_date: null,
              duration: 1,
            },
          ],
          recent_updates: [
            {
              resource_type: "rfi",
              record_id: 20,
              identifier: "RFI-020",
              description: "North Ridge recent update",
              updated_at: "2026-07-27T23:00:00Z",
              target_page: "rfis",
            },
          ],
        })
      );
      await second.promise;
    });
    expect(await screen.findByLabelText("Open RFIs: 1")).toBeInTheDocument();
    expect(screen.getByText("North Ridge question")).toBeInTheDocument();
    expect(screen.getByText("North Ridge mobilization")).toBeInTheDocument();
    expect(screen.getByText("North Ridge recent update")).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("link", { name: /^View RFIs/ })
        .every(
          (link) =>
            link.getAttribute("href") === "#/projects/2/rfis"
        )
    ).toBe(true);

    await act(async () => {
      first.resolve(
        makeDashboard(1, "Riverside", {
          rfis: { total: 5, open: 5, overdue: 2, due_soon: 0 },
          attention_items: [
            {
              resource_type: "rfi",
              record_id: 1,
              identifier: "RFI-001",
              title: "Stale Riverside question",
              due_date: "2026-07-20",
              reason: "Overdue",
              severity: "overdue",
              target_page: "rfis",
            },
          ],
          upcoming_tasks: [
            {
              id: 11,
              name: "Stale Riverside task",
              start_date: "2026-07-28",
              end_date: null,
              duration: null,
            },
          ],
          recent_updates: [
            {
              resource_type: "rfi",
              record_id: 10,
              identifier: "RFI-010",
              description: "Stale Riverside update",
              updated_at: "2026-07-27T22:00:00Z",
              target_page: "rfis",
            },
          ],
        })
      );
      await first.promise;
    });
    expect(screen.getByLabelText("Open RFIs: 1")).toBeInTheDocument();
    expect(screen.queryByLabelText("Open RFIs: 5")).not.toBeInTheDocument();
    expect(screen.queryByText("Stale Riverside question")).not.toBeInTheDocument();
    expect(screen.queryByText("Stale Riverside task")).not.toBeInTheDocument();
    expect(screen.queryByText("Stale Riverside update")).not.toBeInTheDocument();
  });

  it("shows global and local feedback and retries without reloading the app", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchProjectDashboard
      .mockRejectedValueOnce(new ApiError("Service unavailable", 503))
      .mockResolvedValueOnce(
        makeDashboard(1, "Riverside", {
          attention_items: [
            {
              resource_type: "rfi",
              record_id: 7,
              identifier: "RFI-007",
              title: "Loaded after retry",
              due_date: "2026-07-20",
              reason: "Overdue",
              severity: "overdue",
              target_page: "rfis",
            },
          ],
          upcoming_tasks: [
            {
              id: 8,
              name: "Retry schedule task",
              start_date: "2026-07-28",
              end_date: null,
              duration: null,
            },
          ],
          recent_updates: [
            {
              resource_type: "change_order",
              record_id: 8,
              identifier: "CO-008",
              description: "Retry change order update",
              updated_at: "2026-07-27T23:00:00Z",
              target_page: "change-orders",
            },
          ],
        })
      );
    window.location.hash = "#/projects/1/dashboard";

    renderApp();

    expect(
      await screen.findByText(
        "Unable to load project dashboard. Service unavailable"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Project dashboard data could not be loaded. Other project pages remain available."
      )
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Retry dashboard" })
    );

    expect(await screen.findByLabelText("Open RFIs: 0")).toBeInTheDocument();
    expect(screen.getByText("Loaded after retry")).toBeInTheDocument();
    expect(screen.getByText("Retry schedule task")).toBeInTheDocument();
    expect(screen.getByText("Retry change order update")).toBeInTheDocument();
    expect(fetchProjectDashboard).toHaveBeenCalledTimes(2);
    expect(fetchProjects).toHaveBeenCalledOnce();
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
    await screen.findByRole("heading", { name: "Project Dashboard" });
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
    await screen.findByRole("heading", { name: "Project Dashboard" });
    expect(fetchPunchItems).not.toHaveBeenCalled();

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

  it("loads and updates the persistent Schedule Start Date", async () => {
    const user = userEvent.setup();
    const task = {
      id: 1,
      name: "Mobilization",
      duration: 1,
      predecessor: null,
      predecessor_task_id: null,
      dependency_type: "FS",
      lag_days: 0,
      start_date: "2026-03-02",
      end_date: "2026-03-02",
      manual_start_date: null,
      project_id: 1,
      order_index: 1,
      parent_task_id: null,
      is_collapsed: 0,
      is_critical: true,
      total_float: 0,
    };
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchTasks.mockResolvedValue({ tasks: [task] });
    fetchScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-02",
      created_at: "2026-03-02T00:00:00Z",
      updated_at: "2026-03-02T00:00:00Z",
    });
    updateScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-04-06",
      data_date: "2026-03-02",
      created_at: "2026-03-02T00:00:00Z",
      updated_at: "2026-04-01T00:00:00Z",
    });
    window.location.hash = "#/projects/1/schedule";

    renderApp();

    const input = await screen.findByLabelText("Schedule Start Date");
    expect(input).toHaveValue("2026-03-02");
    await user.clear(input);
    await user.type(input, "2026-04-06");
    await user.click(
      screen.getByRole("button", { name: "Update Schedule Start" })
    );
    await user.click(
      screen.getByRole("button", { name: "Recalculate Schedule" })
    );

    await waitFor(() => {
      expect(updateScheduleSettings).toHaveBeenCalledWith(
        1,
        { schedule_start_date: "2026-04-06" },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });
    expect(
      await screen.findByText("Schedule start date updated.")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Schedule Start Date")).toHaveValue(
      "2026-04-06"
    );
    expect(fetchScheduleSettings).toHaveBeenCalledTimes(1);
    expect(fetchTasks).toHaveBeenCalledTimes(2);
  });

  it("updates the Data Date and reloads the canonical task collection once", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-02",
      comparison_baseline_id: null,
    });
    updateScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-09",
      comparison_baseline_id: null,
    });
    window.location.hash = "#/projects/1/schedule";

    renderApp();

    const input = await screen.findByLabelText("Data Date");
    await user.clear(input);
    await user.type(input, "2026-03-09");
    await user.click(screen.getByRole("button", { name: "Update Data Date" }));

    await waitFor(() => {
      expect(updateScheduleSettings).toHaveBeenCalledWith(
        1,
        { data_date: "2026-03-09" },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });
    expect(await screen.findByText("Data Date updated.")).toBeInTheDocument();
    expect(screen.getByLabelText("Data Date")).toHaveValue("2026-03-09");
    expect(fetchTasks).toHaveBeenCalledTimes(2);
    expect(fetchScheduleSettings).toHaveBeenCalledTimes(1);
  });

  it("updates task progress without fetching a second task collection", async () => {
    const user = userEvent.setup();
    const task = {
      id: 1,
      name: "Mobilization",
      duration: 4,
      predecessor: null,
      predecessor_task_id: null,
      dependency_type: "FS",
      lag_days: 0,
      start_date: "2026-03-02",
      end_date: "2026-03-05",
      manual_start_date: null,
      project_id: 1,
      order_index: 1,
      parent_task_id: null,
      is_collapsed: 0,
      progress_status: "not_started",
      percent_complete: 0,
      remaining_duration: 4,
      actual_start_date: null,
      actual_finish_date: null,
      out_of_sequence: false,
    };
    const summary = {
      total_leaf_tasks: 1,
      not_started_count: 1,
      in_progress_count: 0,
      completed_count: 0,
      out_of_sequence_count: 0,
      percent_complete_weighted: 0,
      data_date: "2026-03-09",
      forecast_project_finish: "2026-03-12",
    };
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchTasks.mockResolvedValue({ tasks: [task], summary });
    fetchScheduleSettings.mockResolvedValue({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-09",
      comparison_baseline_id: null,
    });
    updateTaskProgress.mockResolvedValue({
      tasks: [
        {
          ...task,
          progress_status: "in_progress",
          percent_complete: 40,
          remaining_duration: 3,
          actual_start_date: "2026-03-05",
          end_date: "2026-03-11",
        },
      ],
      summary: {
        ...summary,
        not_started_count: 0,
        in_progress_count: 1,
        percent_complete_weighted: 40,
      },
    });
    window.location.hash = "#/projects/1/schedule";

    renderApp();

    await user.click(
      await screen.findByRole("button", {
        name: "Update progress for Mobilization",
      })
    );
    await user.selectOptions(
      screen.getByLabelText("Progress Status"),
      "in_progress"
    );
    await user.type(screen.getByLabelText("Actual Start"), "2026-03-05");
    await user.type(screen.getByLabelText("Percent Complete"), "40");
    await user.clear(screen.getByLabelText("Remaining Duration"));
    await user.type(screen.getByLabelText("Remaining Duration"), "3");
    await user.click(screen.getByRole("button", { name: "Update Progress" }));

    await waitFor(() => {
      expect(updateTaskProgress).toHaveBeenCalledWith(
        1,
        1,
        {
          progress_status: "in_progress",
          actual_start_date: "2026-03-05",
          percent_complete: 40,
          remaining_duration: 3,
        },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });
    expect(await screen.findByText("Task progress updated."))
      .toBeInTheDocument();
    expect(screen.getByText("40% complete")).toBeInTheDocument();
    expect(fetchTasks).toHaveBeenCalledTimes(1);
  });

  it("shows a local schedule load error and retries exactly once", async () => {
    const user = userEvent.setup();
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    fetchTasks
      .mockRejectedValueOnce(new ApiError("Service unavailable", 503))
      .mockResolvedValueOnce({ tasks: [] });
    window.location.hash = "#/projects/1/schedule";

    renderApp();

    expect(
      await screen.findByText("Unable to load the project schedule.")
    ).toBeInTheDocument();
    expect(screen.getByText("Unable to load tasks. Service unavailable"))
      .toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByText(/No tasks yet\. Use Add task below/)
    ).toBeInTheDocument();
    expect(fetchTasks).toHaveBeenCalledTimes(2);
  });

  it("deduplicates initial schedule loads in Strict Mode", async () => {
    fetchProjects.mockResolvedValue({
      projects: [{ id: 1, name: "Riverside" }],
    });
    window.location.hash = "#/projects/1/schedule";

    render(
      <StrictMode>
        <AuthProvider>
          <App />
        </AuthProvider>
      </StrictMode>
    );

    expect(await screen.findByLabelText("Schedule Start Date")).toHaveValue(
      "2026-06-22"
    );
    expect(fetchTasks).toHaveBeenCalledTimes(1);
    expect(fetchScheduleSettings).toHaveBeenCalledTimes(1);
    expect(listScheduleBaselines).toHaveBeenCalledTimes(1);
    expect(fetchScheduleVariance).toHaveBeenCalledTimes(1);
    expect(listLookAheadPlans).toHaveBeenCalledTimes(1);
  });

  it("clears schedule data and settings while switching projects", async () => {
    let resolveTasks;
    let resolveSettings;
    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchTasks.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          tasks: [
            {
              id: 1,
              name: "Riverside task",
              duration: 1,
              project_id: 1,
              dependency_type: "FS",
              lag_days: 0,
              is_collapsed: 0,
            },
          ],
          summary: {
            total_leaf_tasks: 1,
            not_started_count: 0,
            in_progress_count: 1,
            completed_count: 0,
            out_of_sequence_count: 0,
            percent_complete_weighted: 75,
            data_date: "2026-03-09",
            forecast_project_finish: "2026-03-10",
          },
        });
      }
      return new Promise((resolve) => {
        resolveTasks = resolve;
      });
    });
    fetchScheduleSettings.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          project_id: 1,
          schedule_start_date: "2026-03-02",
          data_date: "2026-03-09",
        });
      }
      return new Promise((resolve) => {
        resolveSettings = resolve;
      });
    });
    window.location.hash = "#/projects/1/schedule";

    renderApp();

    expect(await screen.findByText("Riverside task")).toBeInTheDocument();
    expect(screen.getByLabelText("Schedule Start Date")).toHaveValue(
      "2026-03-02"
    );
    expect(screen.getByText("75%", { selector: "dd" })).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/schedule");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await waitFor(() => {
      expect(screen.queryByText("Riverside task")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("75%", { selector: "dd" }))
      .not.toBeInTheDocument();
    expect(screen.queryByLabelText("Schedule Start Date")).not.toBeInTheDocument();

    await act(async () => {
      resolveTasks({
        tasks: [],
        summary: {
          total_leaf_tasks: 0,
          not_started_count: 0,
          in_progress_count: 0,
          completed_count: 0,
          out_of_sequence_count: 0,
          percent_complete_weighted: 0,
          data_date: "2026-05-04",
          forecast_project_finish: null,
        },
      });
      resolveSettings({
        project_id: 2,
        schedule_start_date: "2026-05-04",
        data_date: "2026-05-04",
      });
    });
    expect(await screen.findByLabelText("Schedule Start Date")).toHaveValue(
      "2026-05-04"
    );
    expect(fetchTasks.mock.calls.map(([projectId]) => projectId)).toEqual([
      1,
      2,
    ]);
    expect(
      fetchScheduleSettings.mock.calls.map(([projectId]) => projectId)
    ).toEqual([1, 2]);
  });

  it("drops late schedule and settings responses after a project switch", async () => {
    let resolveOldTasks;
    let resolveOldSettings;
    fetchProjects.mockResolvedValue({
      projects: [
        { id: 1, name: "Riverside" },
        { id: 2, name: "North Ridge" },
      ],
    });
    fetchTasks.mockImplementation((projectId) =>
      projectId === 1
        ? new Promise((resolve) => {
            resolveOldTasks = resolve;
          })
        : Promise.resolve({ tasks: [] })
    );
    fetchScheduleSettings.mockImplementation((projectId) =>
      projectId === 1
        ? new Promise((resolve) => {
            resolveOldSettings = resolve;
          })
        : Promise.resolve({
            project_id: 2,
            schedule_start_date: "2026-05-04",
            data_date: "2026-05-04",
          })
    );
    window.location.hash = "#/projects/1/schedule";

    renderApp();
    await waitFor(() => expect(fetchTasks).toHaveBeenCalledWith(1));
    await act(async () => {
      window.history.pushState({}, "", "#/projects/2/schedule");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByLabelText("Schedule Start Date")).toHaveValue(
      "2026-05-04"
    );

    await act(async () => {
      resolveOldTasks({
        tasks: [{ id: 9, name: "Stale task", duration: 1 }],
      });
      resolveOldSettings({
        project_id: 1,
        schedule_start_date: "2026-03-02",
        data_date: "2026-03-02",
      });
    });

    expect(screen.queryByText("Stale task")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Schedule Start Date")).toHaveValue(
      "2026-05-04"
    );
  });
});
