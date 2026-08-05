import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  archiveLookAheadPlan,
  createLookAheadPlan,
  getLookAheadPlan,
  listLookAheadPlans,
  updateLookAheadItem,
  updateLookAheadPlan,
} from "./api";


const httpMocks = vi.hoisted(() => ({
  authenticatedRequest: vi.fn(),
  downloadAuthenticatedFile: vi.fn(),
  downloadAuthenticatedResponse: vi.fn(),
  jsonRequest: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./httpClient", () => httpMocks);


describe("look-ahead API client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists and reads encoded project plans with cancellation", async () => {
    const signal = new AbortController().signal;
    await listLookAheadPlans("7/unsafe", {
      status: "archived",
      limit: 25,
      offset: 50,
      signal,
    });
    await getLookAheadPlan(7, "2/unsafe", { signal });

    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      1,
      "/projects/7%2Funsafe/look-ahead-plans?status=archived&limit=25&offset=50",
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      2,
      "/projects/7/look-ahead-plans/2%2Funsafe",
      { signal }
    );
  });

  it("creates, updates, archives, and edits item metadata", async () => {
    const signal = new AbortController().signal;
    const plan = { name: "Three Week", anchor_date: "2026-08-10", window_days: 21 };
    await createLookAheadPlan(7, plan, { signal });
    await updateLookAheadPlan(7, 4, { name: "Updated" }, { signal });
    await archiveLookAheadPlan(7, 4, { signal });
    await updateLookAheadItem(
      7,
      4,
      9,
      { readiness_status: "ready" },
      { signal }
    );

    expect(httpMocks.jsonRequest).toHaveBeenNthCalledWith(
      1,
      "/projects/7/look-ahead-plans",
      "POST",
      plan,
      { signal }
    );
    expect(httpMocks.jsonRequest).toHaveBeenNthCalledWith(
      2,
      "/projects/7/look-ahead-plans/4",
      "PUT",
      { name: "Updated" },
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/look-ahead-plans/4/archive",
      { method: "POST", signal }
    );
    expect(httpMocks.jsonRequest).toHaveBeenNthCalledWith(
      3,
      "/projects/7/look-ahead-plans/4/items/9",
      "PUT",
      { readiness_status: "ready" },
      { signal }
    );
  });
});
