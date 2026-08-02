import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  archiveScheduleBaseline,
  createScheduleBaseline,
  fetchScheduleVariance,
  getScheduleBaseline,
  listScheduleBaselines,
  selectScheduleBaseline,
} from "./api";


const httpMocks = vi.hoisted(() => ({
  authenticatedRequest: vi.fn(),
  downloadAuthenticatedFile: vi.fn(),
  downloadAuthenticatedResponse: vi.fn(),
  jsonRequest: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./httpClient", () => httpMocks);


describe("schedule baseline API client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists and reads bounded project baseline data", async () => {
    const signal = new AbortController().signal;
    await listScheduleBaselines("7/unsafe", {
      status: "archived",
      limit: 25,
      offset: 50,
      signal,
    });
    await getScheduleBaseline(7, "2/unsafe", {
      limit: 10,
      offset: 20,
      signal,
    });

    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      1,
      "/projects/7%2Funsafe/schedule-baselines?status=archived&limit=25&offset=50",
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenNthCalledWith(
      2,
      "/projects/7/schedule-baselines/2%2Funsafe?limit=10&offset=20",
      { signal }
    );
  });

  it("creates, archives, and selects with cancellation", async () => {
    const signal = new AbortController().signal;
    const baseline = { name: "Issued Plan", description: null };
    await createScheduleBaseline(7, baseline, { signal });
    await archiveScheduleBaseline(7, 4, { signal });
    await selectScheduleBaseline(7, null, { signal });

    expect(httpMocks.jsonRequest).toHaveBeenNthCalledWith(
      1,
      "/projects/7/schedule-baselines",
      "POST",
      baseline,
      { signal }
    );
    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/schedule-baselines/4/archive",
      { method: "POST", signal }
    );
    expect(httpMocks.jsonRequest).toHaveBeenNthCalledWith(
      2,
      "/projects/7/schedule-baseline-comparison",
      "PUT",
      { baseline_id: null },
      { signal }
    );
  });

  it("encodes every variance filter and AbortSignal", async () => {
    const signal = new AbortController().signal;
    await fetchScheduleVariance(7, {
      baselineId: 4,
      includeSummaries: false,
      status: "slipped",
      criticalChange: "newly_critical",
      search: "steel & deck",
      sort: "finish_variance",
      order: "desc",
      limit: 25,
      offset: 50,
      signal,
    });

    const [url, request] = httpMocks.authenticatedRequest.mock.calls[0];
    expect(url).toBe(
      "/projects/7/schedule-variance?baseline_id=4&include_summaries=false&status=slipped&critical_change=newly_critical&search=steel+%26+deck&sort=finish_variance&order=desc&limit=25&offset=50"
    );
    expect(request).toEqual({ signal });
  });
});
