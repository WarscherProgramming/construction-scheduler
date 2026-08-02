import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchScheduleSettings,
  updateScheduleSettings,
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
});
