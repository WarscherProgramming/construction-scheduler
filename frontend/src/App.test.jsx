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
  createRFI,
  createSubmittal,
  deleteRFI,
  deleteSubmittal,
  fetchChangeOrders,
  fetchDailyLogs,
  fetchInspections,
  fetchNotesDelays,
  fetchProjectCompanies,
  fetchProjects,
  fetchRFIs,
  fetchSubmittals,
  fetchTasks,
  fetchTemplates,
  updateRFI,
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
    fetchRFIs.mockResolvedValue({ rfis: [] });
    createRFI.mockResolvedValue({});
    updateRFI.mockResolvedValue({});
    deleteRFI.mockResolvedValue({ message: "RFI deleted" });
    fetchSubmittals.mockResolvedValue({ submittals: [] });
    createSubmittal.mockResolvedValue({});
    updateSubmittal.mockResolvedValue({});
    deleteSubmittal.mockResolvedValue({ message: "Submittal deleted" });
  });

  it("shows the login experience when unauthenticated", () => {
    localStorage.removeItem("token");

    renderApp();

    expect(
      screen.getByRole("heading", { name: "Welcome back" })
    ).toBeInTheDocument();
    expect(fetchProjects).not.toHaveBeenCalled();
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
    expect(fetchChangeOrders).toHaveBeenCalledWith(1);
    expect(fetchDailyLogs).toHaveBeenCalledWith(1);
    await screen.findByRole("button", {
      name: "RFI health: 0 open, 0 overdue, 0 closed",
    });
    await screen.findByRole("button", {
      name: "Submittal health: 0 active, 0 overdue, 0 approved",
    });
    expect(fetchRFIs).toHaveBeenCalledTimes(1);
    expect(fetchRFIs).toHaveBeenCalledWith(1);
    await waitFor(() => {
      expect(fetchSubmittals).toHaveBeenCalledTimes(1);
    });
    expect(fetchSubmittals).toHaveBeenCalledWith(1);
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
    expect(document.title).toContain("Riverside");
    expect(document.title).toContain("Submittals | FieldFlow");
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
});
