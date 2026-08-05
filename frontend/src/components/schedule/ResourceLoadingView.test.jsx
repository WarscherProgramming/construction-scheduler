import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResourceLoadingView from "./ResourceLoadingView";


const crew = {
  id: 1,
  name: "Electrical Crew",
  trade: "Electrical",
  company: { id: 3, name: "Desert Electric" },
  description: null,
  default_capacity: 4,
  capacity_unit: "workers",
  status: "active",
};
const equipment = {
  id: 2,
  name: "Lift 1",
  equipment_type: "Scissor Lift",
  identifier: "SL-01",
  description: null,
  default_capacity: 1,
  capacity_unit: "units",
  status: "active",
};
const data = {
  project_id: 7,
  data_date: "2026-08-10",
  start_date: "2026-08-10",
  end_date: "2026-08-11",
  summary: {
    active_crews: 1,
    active_equipment_resources: 1,
    assigned_tasks: 2,
    unassigned_executable_tasks: 1,
    unscheduled_tasks: 0,
    over_allocated_resource_days: 1,
    unavailable_resource_conflicts: 0,
    look_ahead_over_allocation_count: 1,
    peak_labor_demand: 5,
    average_labor_demand: 4.5,
    equipment_type_peaks: [],
  },
  resources: [{
    resource: { ...crew, resource_type: "crew", detail: "Electrical", identifier: null },
    days: [
      { date: "2026-08-10", demand: 5, capacity: 4, overage: 1, status: "over_allocated", contributing_tasks: [] },
      { date: "2026-08-11", demand: 4, capacity: 4, overage: 0, status: "within_capacity", contributing_tasks: [] },
    ],
    peak_demand: 5,
    average_demand: 4.5,
    over_allocated_days: 1,
    unavailable_days: 0,
  }],
  conflicts: [{
    date: "2026-08-10",
    resource: { ...crew, resource_type: "crew", detail: "Electrical", identifier: null },
    demand: 5,
    capacity: 4,
    overage: 1,
    status: "over_allocated",
    message: "Demand exceeds capacity by 1 workers.",
    contributing_task_count: 1,
    contributing_tasks_truncated: false,
    contributing_tasks: [{ id: 9, wbs: "1.1", name: "Rough-in" }],
  }],
  total_conflicts: 1,
  conflict_limit: 100,
  conflicts_truncated: false,
  unassigned_tasks: [{ id: 10, wbs: "1.2", name: "Inspection prep", start_date: "2026-08-11", end_date: "2026-08-11", unscheduled: false }],
};

function resourceState(overrides = {}) {
  return {
    crews: [crew],
    equipment: [equipment],
    availability: [],
    isLoading: false,
    isLoadingAvailability: false,
    pendingActions: [],
    isPending: vi.fn(() => false),
    loadAvailability: vi.fn().mockResolvedValue({ availability: [] }),
    createCrew: vi.fn().mockResolvedValue({ crew }),
    updateCrew: vi.fn(),
    archiveCrew: vi.fn(),
    createEquipment: vi.fn(),
    updateEquipment: vi.fn(),
    archiveEquipment: vi.fn(),
    createAvailability: vi.fn(),
    updateAvailability: vi.fn(),
    deleteAvailability: vi.fn(),
    ...overrides,
  };
}

function loadingState(overrides = {}) {
  return {
    data,
    error: null,
    isLoading: false,
    load: vi.fn().mockResolvedValue(data),
    retry: vi.fn().mockResolvedValue(data),
    ...overrides,
  };
}

describe("ResourceLoadingView", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads once and renders factual metrics, conflicts, and accessible cells", async () => {
    const loading = loadingState();
    render(<ResourceLoadingView resources={resourceState()} resourceLoading={loading} />);
    await waitFor(() => expect(loading.load).toHaveBeenCalledOnce());
    expect(screen.getByText("5 workers")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Capacity Conflicts" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Electrical Crew, 08\/10\/2026: demand 5, capacity 4/)).toHaveTextContent("Over by 1");
    expect(screen.getByRole("heading", { name: "Unassigned Executable Tasks" }).closest("section")).toHaveTextContent("Inspection prep");
  });

  it("submits bounded display filters without changing schedule data", async () => {
    const user = userEvent.setup();
    const loading = loadingState();
    render(<ResourceLoadingView resources={resourceState()} resourceLoading={loading} />);
    await user.type(screen.getByLabelText("Start date"), "2026-08-10");
    await user.selectOptions(screen.getByLabelText("Resource type"), "crew");
    await user.click(screen.getByLabelText("Conflicts only"));
    await user.click(screen.getByRole("button", { name: "Apply" }));
    expect(loading.load).toHaveBeenLastCalledWith(expect.objectContaining({
      startDate: "2026-08-10",
      resourceType: "crew",
      overAllocatedOnly: true,
    }));
  });

  it("isolates loading and failure states to the resource panel", async () => {
    const loading = loadingState({ data: null, error: new Error("offline") });
    render(<ResourceLoadingView resources={resourceState()} resourceLoading={loading} />);
    expect(screen.getByRole("alert")).toHaveTextContent("could not be displayed");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(loading.retry).toHaveBeenCalledOnce();
  });

  it("explains when the bounded conflict response omits additional conflicts", () => {
    const boundedData = {
      ...data,
      total_conflicts: 103,
      conflicts_truncated: true,
      conflicts: [{
        ...data.conflicts[0],
        contributing_task_count: 7,
        contributing_tasks_truncated: true,
      }],
    };

    render(
      <ResourceLoadingView
        resources={resourceState()}
        resourceLoading={loadingState({ data: boundedData })}
      />
    );

    expect(screen.getByText(/Showing 1 of 103 conflict days/)).toBeInTheDocument();
    expect(screen.getByText(/and 6 more/)).toBeInTheDocument();
  });

  it("creates crews and opens availability from focused management", async () => {
    const user = userEvent.setup();
    const resources = resourceState();
    render(<ResourceLoadingView resources={resources} resourceLoading={loadingState()} companies={[{ id: 3, name: "Desert Electric" }]} />);
    await user.click(screen.getByRole("button", { name: "Crews" }));
    const form = screen.getByRole("button", { name: "Add Crew" }).closest("form");
    await user.type(within(form).getByLabelText("Name"), "Concrete Crew");
    await user.clear(within(form).getByLabelText(/Default capacity/));
    await user.type(within(form).getByLabelText(/Default capacity/), "6");
    await user.click(within(form).getByRole("button", { name: "Add Crew" }));
    expect(resources.createCrew).toHaveBeenCalledWith(expect.objectContaining({ name: "Concrete Crew", default_capacity: 6 }));
    await user.click(screen.getByRole("button", { name: "Availability" }));
    expect(screen.getByRole("dialog", { name: "Resource Availability" })).toBeInTheDocument();
    expect(resources.loadAvailability).toHaveBeenCalledWith("crew", 1);
  });
});
