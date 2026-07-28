import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchProjectDashboard } from "./api";


const httpMocks = vi.hoisted(() => ({
  authenticatedRequest: vi.fn(),
  downloadAuthenticatedFile: vi.fn(),
  downloadAuthenticatedResponse: vi.fn(),
  jsonRequest: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./httpClient", () => httpMocks);


describe("dashboard API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.authenticatedRequest.mockResolvedValue({ project: { id: 7 } });
  });

  it("requests the encoded project dashboard with a required as_of date", async () => {
    const signal = new AbortController().signal;

    await fetchProjectDashboard("project/7", "2026-07-27", { signal });

    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/project%2F7/dashboard?as_of=2026-07-27",
      { signal }
    );
  });

  it("URL-encodes the as_of query and forwards normalized failures", async () => {
    const error = new Error("Normalized request failure");
    httpMocks.authenticatedRequest.mockRejectedValue(error);

    await expect(
      fetchProjectDashboard(7, "2026-07-27+local")
    ).rejects.toBe(error);
    expect(httpMocks.authenticatedRequest).toHaveBeenCalledWith(
      "/projects/7/dashboard?as_of=2026-07-27%2Blocal",
      { signal: undefined }
    );
  });
});
