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
  updateTaskProgress: vi.fn(),
}));

import useScheduleActions from "./useScheduleActions";
import {
  applyTemplate,
  createTask,
  deleteTask,
  reorderTasks,
  updateScheduleSettings,
  updateTask,
  updateTaskProgress,
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
    setScheduleSummary: vi.fn(),
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
      settingsMutation = result.current.handleUpdateDataDate("2026-03-09");
    });

    await switchProject();
    templateRequest.resolve({ message: "Template applied" });
    settingsRequest.resolve({
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-09",
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

  it("updates progress through the canonical task response", async () => {
    const summary = { completed_count: 1 };
    const completedTasks = [
      {
        ...tasks[0],
        progress_status: "completed",
        percent_complete: 100,
      },
    ];
    updateTaskProgress.mockResolvedValue({
      tasks: completedTasks,
      summary,
    });
    const { result, spies } = setup();

    act(() => result.current.openTaskProgress(tasks[0]));
    expect(result.current.progressTaskId).toBe(1);
    await act(async () => {
      await result.current.handleUpdateTaskProgress(1, {
        progress_status: "completed",
        actual_start_date: "2026-03-02",
        actual_finish_date: "2026-03-05",
      });
    });

    expect(updateTaskProgress).toHaveBeenCalledWith(
      1,
      1,
      {
        progress_status: "completed",
        actual_start_date: "2026-03-02",
        actual_finish_date: "2026-03-05",
      },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(spies.setTasks).toHaveBeenCalledWith(completedTasks);
    expect(spies.setScheduleSummary).toHaveBeenCalledWith(summary);
    expect(result.current.progressTaskId).toBeNull();
    expect(spies.showNotice).toHaveBeenCalledWith(
      "success",
      "Task progress updated."
    );
  });

  it("updates advanced planning through the canonical task response", async () => {
    const planning = {
      duration: 0,
      is_milestone: true,
      constraint_type: "SNET",
      constraint_date: "2026-03-09",
      dependencies: [
        {
          predecessor_task_id: 2,
          dependency_type: "FF",
          lag_days: -2,
        },
      ],
    };
    const updatedTasks = [{ ...tasks[0], ...planning }];
    updateTask.mockResolvedValue({ tasks: updatedTasks, summary: {} });
    const { result, spies } = setup();

    act(() => result.current.openTaskPlanning(tasks[0]));
    expect(result.current.planningTaskId).toBe(1);
    await act(async () => {
      await result.current.handleUpdateTaskPlanning(1, planning);
    });

    expect(updateTask).toHaveBeenCalledWith(
      1,
      1,
      planning,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(spies.setTasks).toHaveBeenCalledWith(updatedTasks);
    expect(result.current.planningTaskId).toBeNull();
    expect(spies.showNotice).toHaveBeenCalledWith(
      "success",
      "Task planning updated."
    );
  });

  it("clears planning selection and ignores its stale response on switch", async () => {
    const request = deferred();
    updateTask.mockReturnValue(request.promise);
    const { result, spies, switchProject } = setup();
    act(() => result.current.openTaskPlanning(tasks[0]));
    let mutation;
    act(() => {
      mutation = result.current.handleUpdateTaskPlanning(1, {
        duration: 1,
        is_milestone: false,
        constraint_type: "ASAP",
        constraint_date: null,
        dependencies: [],
      });
    });

    await switchProject();
    expect(result.current.planningTaskId).toBeNull();
    request.resolve({ tasks: [], summary: {} });
    await act(async () => mutation);

    expect(spies.setTasks).not.toHaveBeenCalled();
    expect(spies.showNotice).not.toHaveBeenCalled();
  });

  it("deduplicates progress updates and ignores stale success", async () => {
    const request = deferred();
    updateTaskProgress.mockReturnValue(request.promise);
    const { result, spies, switchProject } = setup();
    act(() => result.current.openTaskProgress(tasks[0]));
    let first;
    act(() => {
      first = result.current.handleUpdateTaskProgress(1, {
        progress_status: "not_started",
      });
      void result.current.handleUpdateTaskProgress(1, {
        progress_status: "not_started",
      });
    });

    expect(updateTaskProgress).toHaveBeenCalledTimes(1);
    await switchProject();
    expect(result.current.progressTaskId).toBeNull();
    request.resolve({ tasks: [], summary: { completed_count: 0 } });
    await act(async () => first);

    expect(spies.setTasks).not.toHaveBeenCalled();
    expect(spies.setScheduleSummary).not.toHaveBeenCalled();
    expect(spies.showNotice).not.toHaveBeenCalled();
  });

  it("ignores stale progress and Data Date failures", async () => {
    const progressRequest = deferred();
    const settingsRequest = deferred();
    updateTaskProgress.mockReturnValue(progressRequest.promise);
    updateScheduleSettings.mockReturnValue(settingsRequest.promise);
    const { result, spies, switchProject } = setup();
    let progressMutation;
    let settingsMutation;
    act(() => {
      progressMutation = result.current.handleUpdateTaskProgress(1, {
        progress_status: "not_started",
      });
      settingsMutation = result.current.handleUpdateDataDate("2026-03-09");
    });

    await switchProject();
    progressRequest.reject(new Error("stale progress failure"));
    settingsRequest.reject(new Error("stale settings failure"));
    await act(async () => Promise.all([progressMutation, settingsMutation]));

    expect(spies.reportRequestError).not.toHaveBeenCalled();
    expect(spies.setScheduleSettings).not.toHaveBeenCalled();
    expect(spies.loadTasks).not.toHaveBeenCalled();
  });

  it("updates the Data Date, reloads tasks once, and keeps global feedback", async () => {
    const updatedSettings = {
      project_id: 1,
      schedule_start_date: "2026-03-02",
      data_date: "2026-03-09",
    };
    updateScheduleSettings.mockResolvedValue(updatedSettings);
    const { result, spies } = setup();

    await act(async () => {
      await result.current.handleUpdateDataDate("2026-03-09");
    });

    expect(updateScheduleSettings).toHaveBeenCalledWith(
      1,
      { data_date: "2026-03-09" },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(spies.setScheduleSettings).toHaveBeenCalledWith(updatedSettings);
    expect(spies.loadTasks).toHaveBeenCalledOnce();
    expect(spies.showNotice).toHaveBeenCalledWith(
      "success",
      "Data Date updated."
    );
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

  it("routes a current progress session failure through global handling", async () => {
    const error = Object.assign(new Error("Session expired"), { status: 401 });
    updateTaskProgress.mockRejectedValue(error);
    const { result, spies } = setup();

    await act(async () => {
      await result.current.handleUpdateTaskProgress(1, {
        progress_status: "not_started",
      });
    });

    expect(spies.reportRequestError).toHaveBeenCalledWith(
      "Unable to update task progress",
      error
    );
  });
});
