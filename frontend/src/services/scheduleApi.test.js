import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchScheduleHealth,
  fetchScheduleSettings,
  fetchTasks,
  updateScheduleSettings,
  updateTaskProgress,
} from "./api";


const httpMocks = vi.hoisted(() => ({
  authenticatedRequest: vi.fn(),
  downloadAuthenticatedFile: vi.fn(),
  downloadAuthenticatedResponse: vi.fn(),
  jsonRequest: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./httpClient", () => httpMocks);


describe("schedule settings API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads project-scoped schedule settings", async () => {
    await fetchScheduleSettings(7);

    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/schedule-settings"
    );
  });

  it("loads schedule health with an optional baseline and cancellation", async () => {
    const signal = new AbortController().signal;

    await fetchScheduleHealth(7, { baselineId: 12, signal });

    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/schedule-health?baseline_id=12",
      { signal }
    );
  });

  it("updates only the schedule settings payload and forwards cancellation", async () => {
    const signal = new AbortController().signal;
    const payload = { schedule_start_date: "2026-04-06" };

    await updateScheduleSettings(7, payload, { signal });

    expect(httpMocks.jsonRequest).toHaveBeenCalledWith(
      "/projects/7/schedule-settings",
      "PUT",
      payload,
      { signal }
    );
  });

  it("loads the canonical task collection with cancellation support", async () => {
    const signal = new AbortController().signal;

    await fetchTasks(7, { signal });

    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/tasks",
      { signal }
    );
  });

  it("preserves the task request shape when no signal is supplied", async () => {
    await fetchTasks(7);

    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/tasks"
    );
  });

  it("updates progress through the focused project task route", async () => {
    const signal = new AbortController().signal;
    const payload = {
      progress_status: "in_progress",
      actual_start_date: "2026-03-05",
      percent_complete: 40,
      remaining_duration: 3,
    };

    await updateTaskProgress(7, 11, payload, { signal });

    expect(httpMocks.jsonRequest).toHaveBeenCalledWith(
      "/projects/7/tasks/11/progress",
      "PUT",
      payload,
      { signal }
    );
  });
});
