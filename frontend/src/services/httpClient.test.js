import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  authenticatedRequest,
  configureAuthentication,
  request,
} from "./httpClient";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("httpClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    // Module-level auth state persists between tests; reset it.
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("attaches the bearer token to authenticated requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: vi.fn() });

    await authenticatedRequest("/projects");

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer token-123"
    );
  });

  it("invokes the unauthorized handler on 401 and throws an ApiError", async () => {
    const onUnauthorized = vi.fn();
    // Response bodies are single-use; build a fresh one per call.
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(jsonResponse({ detail: "Invalid token" }, 401))
      )
    );
    configureAuthentication({ token: "expired", onUnauthorized });

    await expect(authenticatedRequest("/projects")).rejects.toBeInstanceOf(
      ApiError
    );
    await expect(authenticatedRequest("/projects")).rejects.toMatchObject({
      status: 401,
      message: "Invalid token",
    });
    expect(onUnauthorized).toHaveBeenCalledTimes(2);
  });

  it("joins validation error arrays into one message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            detail: [
              { msg: "name is required" },
              { msg: "duration must be positive" },
            ],
          },
          422
        )
      )
    );

    await expect(request("/tasks")).rejects.toMatchObject({
      status: 422,
      message: "name is required, duration must be positive",
    });
  });

  it("falls back to a status message for non-JSON error bodies", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("oops", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        })
      )
    );

    await expect(request("/anything")).rejects.toMatchObject({
      status: 500,
      message: "Request failed with status 500",
    });
  });

  it("wraps network failures in an ApiError with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(request("/anything")).rejects.toMatchObject({
      status: 0,
      message: "Unable to connect to the API",
    });
  });

  it("resolves 204 responses as null", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    );

    await expect(request("/deleted")).resolves.toBeNull();
  });
});
