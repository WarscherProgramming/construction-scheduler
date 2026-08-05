import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  archiveCrew,
  createCrew,
  createResourceAvailability,
  createTaskResourceAssignment,
  deleteResourceAvailability,
  deleteTaskResourceAssignment,
  fetchResourceLoading,
  listCrews,
  listEquipmentResources,
  listResourceAvailability,
  listTaskResourceAssignments,
  updateResourceAvailability,
  updateTaskResourceAssignment,
} from "./api";


const httpMocks = vi.hoisted(() => ({
  authenticatedRequest: vi.fn(),
  downloadAuthenticatedFile: vi.fn(),
  downloadAuthenticatedResponse: vi.fn(),
  jsonRequest: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./httpClient", () => httpMocks);


describe("resource planning API client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses bounded project resource and loading queries", async () => {
    const signal = new AbortController().signal;
    await listCrews("7/unsafe", { status: "active", limit: 25, offset: 5, signal });
    await listEquipmentResources(7, { signal });
    await fetchResourceLoading(7, {
      startDate: "2026-08-10",
      endDate: "2026-08-30",
      resourceType: "crew",
      companyId: 4,
      trade: "Electrical",
      overAllocatedOnly: true,
      includeUnassigned: false,
    }, { signal });

    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      1,
      "/projects/7%2Funsafe/crews?status=active&limit=25&offset=5",
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      2,
      "/projects/7/equipment-resources?status=all&limit=200&offset=0",
      { signal }
    );
    expect(httpMocks.authenticatedRequest.mock.calls[2][0]).toContain(
      "/projects/7/resource-loading?start_date=2026-08-10&end_date=2026-08-30"
    );
    expect(httpMocks.authenticatedRequest.mock.calls[2][0]).toContain(
      "over_allocated_only=true"
    );
  });

  it("maps CRUD operations to task and typed-resource endpoints", async () => {
    const signal = new AbortController().signal;
    await createCrew(7, { name: "Crew A" }, { signal });
    await archiveCrew(7, 2, { signal });
    await listTaskResourceAssignments(7, 9, { signal });
    await createTaskResourceAssignment(7, 9, { resource_type: "crew" }, { signal });
    await updateTaskResourceAssignment(7, 9, 3, { allocation_amount: 4 }, { signal });
    await deleteTaskResourceAssignment(7, 9, 3, { signal });
    await listResourceAvailability(7, "crew", 2, { signal });
    await createResourceAvailability(7, "crew", 2, { capacity: 0 }, { signal });
    await updateResourceAvailability(7, "crew", 2, 5, { capacity: 3 }, { signal });
    await deleteResourceAvailability(7, "crew", 2, 5, { signal });

    expect(httpMocks.jsonRequest).toHaveBeenCalledWith(
      "/projects/7/tasks/9/resource-assignments/3",
      "PUT",
      { allocation_amount: 4 },
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/resources/crew/2/availability/5",
      { method: "DELETE", signal }
    );
  });
});
