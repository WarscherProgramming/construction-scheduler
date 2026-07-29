import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  authenticatedRequest,
  clearAuthentication,
  configureAuthentication,
  logoutAuthentication,
  request,
  restoreAuthentication,
} from "./httpClient";


function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


function session(token = "refreshed-token") {
  return {
    access_token: token,
    token_type: "bearer",
    csrf_token: "csrf",
    user: { id: 1, email: "user@example.com" },
  };
}


describe("httpClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAuthentication();
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("attaches the in-memory bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: vi.fn() });

    await authenticatedRequest("/projects");

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer token-123"
    );
  });

  it("refreshes once and retries a protected request once after 401", async () => {
    let projectCalls = 0;
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse(session()));
      }
      projectCalls += 1;
      return Promise.resolve(
        projectCalls === 1
          ? jsonResponse({ detail: "Expired" }, 401)
          : jsonResponse({
              authorization: options.headers.Authorization,
            })
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "expired", onUnauthorized: vi.fn() });

    await expect(authenticatedRequest("/projects")).resolves.toEqual({
      authorization: "Bearer refreshed-token",
    });
    expect(projectCalls).toBe(2);
    expect(
      fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))
    ).toHaveLength(1);
  });

  it("deduplicates refresh for five concurrent 401 responses", async () => {
    let refreshCalls = 0;
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        return Promise.resolve(jsonResponse(session()));
      }
      return Promise.resolve(
        options.headers.Authorization === "Bearer expired"
          ? jsonResponse({ detail: "Expired" }, 401)
          : jsonResponse({ ok: true })
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "expired", onUnauthorized: vi.fn() });

    await expect(
      Promise.all(
        Array.from({ length: 5 }, () => authenticatedRequest("/projects"))
      )
    ).resolves.toEqual(Array.from({ length: 5 }, () => ({ ok: true })));
    expect(refreshCalls).toBe(1);
  });

  it("notifies once when a shared refresh is rejected", async () => {
    const onUnauthorized = vi.fn();
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse({ detail: "Invalid" }, 401));
      }
      return Promise.resolve(jsonResponse({ detail: "Expired" }, 401));
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "expired", onUnauthorized });

    const results = await Promise.allSettled(
      Array.from({ length: 5 }, () => authenticatedRequest("/projects"))
    );

    expect(results.every(({ status }) => status === "rejected")).toBe(true);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("does not refresh a 403 or a public 401", async () => {
    const onUnauthorized = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Forbidden" }, 403))
      .mockResolvedValueOnce(jsonResponse({ detail: "Bad login" }, 401));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token", onUnauthorized });

    await expect(authenticatedRequest("/projects")).rejects.toMatchObject({
      status: 403,
    });
    await expect(request("/auth/login")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("does not loop when the retried request is still unauthorized", async () => {
    const onUnauthorized = vi.fn();
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse(session()));
      }
      return Promise.resolve(jsonResponse({ detail: "Denied" }, 401));
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "expired", onUnauthorized });

    await expect(authenticatedRequest("/projects")).rejects.toMatchObject({
      status: 401,
    });
    expect(
      fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))
    ).toHaveLength(1);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("rejects malformed refresh responses and keeps startup failures quiet", async () => {
    const onUnauthorized = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve(
          url.endsWith("/auth/csrf")
            ? jsonResponse({ csrf_token: "csrf" })
            : jsonResponse({ token_type: "bearer" })
        )
      )
    );
    configureAuthentication({ token: null, onUnauthorized });

    await expect(restoreAuthentication()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("preserves validation, network, and empty-response error behavior", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(
            { detail: [{ msg: "name required" }, { msg: "invalid date" }] },
            422
          )
        )
        .mockRejectedValueOnce(new TypeError("offline"))
        .mockResolvedValueOnce(new Response(null, { status: 204 }))
    );

    await expect(request("/tasks")).rejects.toMatchObject({
      status: 422,
      message: "name required, invalid date",
    });
    await expect(request("/tasks")).rejects.toMatchObject({ status: 0 });
    await expect(request("/tasks")).resolves.toBeNull();
  });

  it("logs out safely while a refresh is pending", async () => {
    let resolveRefresh;
    let refreshStarted;
    const started = new Promise((resolve) => {
      refreshStarted = resolve;
    });
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        refreshStarted();
        return new Promise((resolve) => {
          resolveRefresh = resolve;
        });
      }
      if (url.endsWith("/auth/logout")) {
        return Promise.resolve(jsonResponse({ message: "Logged out" }));
      }
      return Promise.resolve(jsonResponse({ detail: "Expired" }, 401));
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "expired", onUnauthorized: vi.fn() });
    const protectedRequest = authenticatedRequest("/projects");
    await started;

    const logout = logoutAuthentication();
    resolveRefresh(jsonResponse(session()));

    await expect(protectedRequest).rejects.toBeInstanceOf(ApiError);
    await expect(logout).resolves.toEqual({ message: "Logged out" });
    expect(
      fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/logout"))
    ).toHaveLength(1);
  });
});
