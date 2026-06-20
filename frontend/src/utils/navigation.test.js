import { beforeEach, describe, expect, it } from "vitest";

import {
  buildAppHash,
  parseAppHash,
  updateBrowserRoute,
} from "./navigation";


describe("navigation utilities", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "#/");
  });

  it("builds stable project module hashes", () => {
    expect(buildAppHash("dailyLogs", 42)).toBe("#/projects/42/daily-logs");
    expect(buildAppHash("home", 42)).toBe("#/");
  });

  it("parses known routes and rejects invalid routes", () => {
    expect(parseAppHash("#/projects/42/change-orders")).toEqual({
      page: "changeOrders",
      projectId: 42,
    });
    expect(parseAppHash("#/projects/nope/dashboard")).toEqual({
      page: "home",
      projectId: null,
    });
    expect(parseAppHash("#/unknown")).toEqual({
      page: "home",
      projectId: null,
    });
  });

  it("updates browser history with push and replace semantics", () => {
    updateBrowserRoute("scheduler", 7);

    expect(window.location.hash).toBe("#/projects/7/schedule");
    expect(window.history.state).toEqual({
      page: "scheduler",
      projectId: 7,
    });

    updateBrowserRoute("home", null, { replace: true });

    expect(window.location.hash).toBe("#/");
    expect(window.history.state).toEqual({
      page: "home",
      projectId: null,
    });
  });
});
