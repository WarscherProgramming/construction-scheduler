import { render, screen } from "@testing-library/react";
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
  fetchChangeOrders,
  fetchDailyLogs,
  fetchInspections,
  fetchNotesDelays,
  fetchProjectCompanies,
  fetchProjects,
  fetchTasks,
  fetchTemplates,
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
});
