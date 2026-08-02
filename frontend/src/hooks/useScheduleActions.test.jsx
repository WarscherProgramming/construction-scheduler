import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  applyTemplate: vi.fn(),
  createTask: vi.fn(),
  deleteTask: vi.fn(),
  exportProjectPdf: vi.fn(),
  reorderTasks: vi.fn(),
  saveTemplate: vi.fn(),
  updateScheduleSettings: vi.fn(),
  updateTask: vi.fn(),
}));

import useScheduleActions from "./useScheduleActions";
import {
  applyTemplate,
  createTask,
  deleteTask,
  reorderTasks,
  updateScheduleSettings,
  updateTask,
} from "../services/api";


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

const tasks = [
  {
    id: 1,
    name: "First",
    duration: 1,
    predecessor: null,
    parent_task_id: null,
    is_collapsed: 0,
  },
  {
    id: 2,
    name: "Second",
    duration: 1,
    predecessor: null,
    parent_task_id: null,
    is_collapsed: 0,
  },
];

function setup(overrides = {}) {
  const projectRef = { current: 1 };
  const spies = {
    setTasks: vi.fn(),
    setTemplates: vi.fn(),
    setScheduleSettings: vi.fn(),
    loadTasks: vi.fn().mockResolvedValue(undefined),
    showNotice: vi.fn(),
    reportRequestError: vi.fn(),
    reportValidationError: vi.fn(),
  };
  const props = {
    selectedProjectId: 1,
    selectedProjectIdRef: projectRef,
    tasks,
    runOperation: async (key, operation) => operation(),
    ...spies,
    ...overrides,
  };
  const hook = renderHook(
    ({ selectedProjectId }) =>
      useScheduleActions({ ...props, selectedProjectId }),
    { initialProps: { selectedProjectId: 1 } }
  );

  const switchProject = async (projectId = 2) => {
    projectRef.current = projectId;
    hook.rerender({ selectedProjectId: projectId });
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });
  };

  return { ...hook, projectRef, spies, switchProject };
}


describe("useScheduleActions project mutation safety", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends null only for supported field-clearing semantics", async () => {
    updateTask.mockResolvedValue({ tasks });
    const { result } = setup();

    act(() => {
      result.current.handleCellClick(tasks[0], "manual_start_date");
      result.current.setEditValue("");
    });
    await act(async () => {
      await result.current.handleCellSave(tasks[0]);
    });

    expect(updateTask).toHaveBeenCalledWith(
      1,
      1,
      { manual_start_date: null },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );

    act(() => {
      result.current.handleCellClick(tasks[0], "predecessor");
      result.current.setEditValue("");
    });
    await act(async () => {
      await result.current.handleCellSave(tasks[0]);
    });
    expect(updateTask).toHaveBeenLastCalledWith(
      1,
      1,
      { predecessor: null },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("blocks invalid duration before issuing a request", async () => {
    const { result, spies } = setup();
    act(() => {
      result.current.handleCellClick(tasks[0], "duration");
      result.current.setEditValue("0");
    });

    await act(async () => {
      await result.current.handleCellSave(tasks[0]);
    });

    expect(updateTask).not.toHaveBeenCalled();
    expect(spies.reportValidationError).toHaveBeenCalledWith(
      "Enter a whole number of workdays from 1 to 36500."
    );
  });

  it("ignores a create response after a project switch", async () => {
    const request = deferred();
    createTask.mockReturnValue(request.promise);
    const { result, spies, switchProject } = setup();
    const emptyTask = {
      id: null,
      name: "",
      duration: "",
      manual_start_date: "",
      predecessor: "",
    };
    act(() => {
      result.current.handleCellClick(emptyTask, "name");
      result.current.setEditValue("New task");
    });
    let mutation;
    act(() => {
      mutation = result.current.handleCellSave(emptyTask);
    });

    await switchProject();
    request.resolve({ tasks: [{ id: 9, name: "Stale" }] });
    await act(async () => mutation);

    expect(spies.setTasks).not.toHaveBeenCalled();
    expect(spies.reportRequestError).not.toHaveBeenCalled();
  });

  it("ignores update and delete responses after a project switch", async () => {
    const updateRequest = deferred();
    const deleteRequest = deferred();
    updateTask.mockReturnValue(updateRequest.promise);
    deleteTask.mockReturnValue(deleteRequest.promise);
    const { result, spies, switchProject } = setup();
    let updateMutation;
    let deleteMutation;
    act(() => {
      updateMutation = result.current.handleToggleCollapse(tasks[0]);
      deleteMutation = result.current.performTaskDelete(tasks[1].id);
    });

    await switchProject();
    updateRequest.resolve({ tasks: [{ id: 1, is_collapsed: 1 }] });
    deleteRequest.resolve({ tasks: [] });
    await act(async () => Promise.all([updateMutation, deleteMutation]));

    expect(spies.setTasks).not.toHaveBeenCalled();
    expect(spies.showNotice).not.toHaveBeenCalled();
  });

  it("does not restore an old collection when stale reorder fails", async () => {
    const request = deferred();
    reorderTasks.mockReturnValue(request.promise);
    const { result, spies, switchProject } = setup();
    let mutation;
    act(() => {
      mutation = result.current.handleDragEnd({
        active: { id: 1 },
        over: { id: 2 },
      });
    });
    expect(spies.setTasks).toHaveBeenCalledTimes(1);

    await switchProject();
    request.reject(new Error("late failure"));
    await act(async () => mutation);

    expect(spies.setTasks).toHaveBeenCalledTimes(1);
    expect(spies.reportRequestError).not.toHaveBeenCalled();
  });

  it("ignores stale template and settings responses", async () => {
    const templateRequest = deferred();
    const settingsRequest = deferred();
    applyTemplate.mockReturnValue(templateRequest.promise);
    updateScheduleSettings.mockReturnValue(settingsRequest.promise);
    const { result, spies, switchProject } = setup();
    act(() => result.current.setSelectedTemplateId("7"));
    let templateMutation;
    let settingsMutation;
    act(() => {
      templateMutation = result.current.handleApplyTemplate();
      settingsMutation = result.current.handleUpdateScheduleStart(
        "2026-04-06"
      );
    });

    await switchProject();
    templateRequest.resolve({ message: "Template applied" });
    settingsRequest.resolve({
      project_id: 1,
      schedule_start_date: "2026-04-06",
    });
    await act(async () => Promise.all([templateMutation, settingsMutation]));

    expect(spies.loadTasks).not.toHaveBeenCalled();
    expect(spies.setScheduleSettings).not.toHaveBeenCalled();
    expect(spies.showNotice).not.toHaveBeenCalled();
  });

  it("ignores stale mutation failures and clears interaction state", async () => {
    const request = deferred();
    deleteTask.mockReturnValue(request.promise);
    const { result, spies, switchProject } = setup();
    act(() => {
      result.current.setSelectedTaskId(1);
      result.current.handleCellClick(tasks[0], "name");
    });
    let mutation;
    act(() => {
      mutation = result.current.performTaskDelete(1);
    });

    await switchProject();
    request.reject(new Error("old project failed"));
    await act(async () => mutation);

    expect(result.current.selectedTaskId).toBeNull();
    expect(result.current.editingCell).toBeNull();
    expect(spies.reportRequestError).not.toHaveBeenCalled();
  });

  it("deduplicates an in-flight mutation and clears pending on switch", async () => {
    const request = deferred();
    deleteTask.mockReturnValue(request.promise);
    const { result, switchProject } = setup();
    let first;
    act(() => {
      first = result.current.performTaskDelete(1);
      void result.current.performTaskDelete(1);
    });

    expect(deleteTask).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(result.current.isScheduleMutationActive("deleteTask:1")).toBe(true);
    });
    await switchProject();
    expect(result.current.isScheduleMutationActive("deleteTask:1")).toBe(false);

    request.resolve({ tasks: [] });
    await act(async () => first);
  });

  it("reports a current-project session failure through global handling", async () => {
    deleteTask.mockRejectedValue(new Error("Session expired"));
    const { result, spies } = setup();

    await act(async () => {
      await result.current.performTaskDelete(1);
    });

    expect(spies.reportRequestError).toHaveBeenCalledWith(
      "Unable to delete task",
      expect.objectContaining({ message: "Session expired" })
    );
  });
});
