import { fireEvent, render, screen } from "@testing-library/react";
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
  deleteRFI,
  fetchChangeOrders,
  fetchDailyLogs,
  fetchInspections,
  fetchNotesDelays,
  fetchProjectCompanies,
  fetchProjects,
  fetchRFIs,
  fetchTasks,
  fetchTemplates,
  updateRFI,
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
});
