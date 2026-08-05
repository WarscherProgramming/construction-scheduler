import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useProjectResources from "./useProjectResources";


const api = vi.hoisted(() => ({
  archiveCrew: vi.fn(),
  archiveEquipmentResource: vi.fn(),
  createCrew: vi.fn(),
  createEquipmentResource: vi.fn(),
  createResourceAvailability: vi.fn(),
  createTaskResourceAssignment: vi.fn(),
  deleteResourceAvailability: vi.fn(),
  deleteTaskResourceAssignment: vi.fn(),
  listCrews: vi.fn(),
  listEquipmentResources: vi.fn(),
  listResourceAvailability: vi.fn(),
  listTaskResourceAssignments: vi.fn(),
  updateCrew: vi.fn(),
  updateEquipmentResource: vi.fn(),
  updateResourceAvailability: vi.fn(),
  updateTaskResourceAssignment: vi.fn(),
}));

vi.mock("../services/api", () => api);

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function props(overrides = {}) {
  return {
    projectId: 7,
    enabled: true,
    showNotice: vi.fn(),
    reportRequestError: vi.fn(),
    ...overrides,
  };
}

describe("useProjectResources", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.listCrews.mockResolvedValue({ crews: [{ id: 1, name: "Crew A" }] });
    api.listEquipmentResources.mockResolvedValue({ equipment: [{ id: 2, name: "Lift" }] });
    api.listTaskResourceAssignments.mockResolvedValue({ assignments: [] });
    api.listResourceAvailability.mockResolvedValue({ availability: [] });
  });

  it("loads each project resource collection exactly once", async () => {
    const { result } = renderHook(() => useProjectResources(props()));
    await waitFor(() => expect(result.current.crews).toHaveLength(1));
    expect(api.listCrews).toHaveBeenCalledOnce();
    expect(api.listEquipmentResources).toHaveBeenCalledOnce();
    expect(result.current.equipment[0].name).toBe("Lift");
  });

  it("loads assignments and availability only when requested", async () => {
    api.listTaskResourceAssignments.mockResolvedValue({ assignments: [{ id: 4 }] });
    api.listResourceAvailability.mockResolvedValue({ availability: [{ id: 5 }] });
    const { result } = renderHook(() => useProjectResources(props()));
    await waitFor(() => expect(result.current.crews).toHaveLength(1));
    expect(api.listTaskResourceAssignments).not.toHaveBeenCalled();
    await act(async () => result.current.loadAssignments(9));
    expect(result.current.assignments).toEqual([{ id: 4 }]);
    await act(async () => result.current.loadAvailability("crew", 1));
    expect(result.current.availability).toEqual([{ id: 5 }]);
  });

  it("clears project state and rejects an older response", async () => {
    const oldCrews = deferred();
    const oldEquipment = deferred();
    api.listCrews.mockReturnValueOnce(oldCrews.promise).mockResolvedValueOnce({ crews: [{ id: 8 }] });
    api.listEquipmentResources.mockReturnValueOnce(oldEquipment.promise).mockResolvedValueOnce({ equipment: [] });
    const { result, rerender } = renderHook(
      ({ projectId }) => useProjectResources(props({ projectId })),
      { initialProps: { projectId: 7 } }
    );
    await waitFor(() => expect(api.listCrews).toHaveBeenCalledOnce());
    rerender({ projectId: 8 });
    await waitFor(() => expect(result.current.crews).toEqual([{ id: 8 }]));
    await act(async () => {
      oldCrews.resolve({ crews: [{ id: 1 }] });
      oldEquipment.resolve({ equipment: [{ id: 2 }] });
    });
    expect(result.current.projectId).toBe(8);
    expect(result.current.crews).toEqual([{ id: 8 }]);
  });

  it("refreshes assignments after a successful mutation", async () => {
    api.createTaskResourceAssignment.mockResolvedValue({ assignment: { id: 4 } });
    api.listTaskResourceAssignments
      .mockResolvedValueOnce({ assignments: [] })
      .mockResolvedValueOnce({ assignments: [{ id: 4 }] });
    const showNotice = vi.fn();
    const { result } = renderHook(() => useProjectResources(props({ showNotice })));
    await waitFor(() => expect(result.current.crews).toHaveLength(1));
    await act(async () => result.current.loadAssignments(9));
    await act(async () => result.current.createAssignment(9, {
      resource_type: "crew",
      resource_id: 1,
      allocation_amount: 2,
    }));
    expect(result.current.assignments).toEqual([{ id: 4 }]);
    expect(showNotice).toHaveBeenCalledWith("success", "Resource assigned.");
  });
});
