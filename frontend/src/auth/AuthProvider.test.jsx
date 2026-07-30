import { act, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthProvider from "./AuthProvider";
import { useAuth } from "./authContext";
import { fetchProjects } from "../services/api";


function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


function session(token = "session-token") {
  return {
    access_token: token,
    token_type: "bearer",
    csrf_token: "csrf-token",
    user: { id: 1, email: "user@example.com" },
  };
}


function AuthHarness() {
  const {
    authStatus,
    isAuthenticated,
    login,
    logout,
    retryStartup,
  } = useAuth();

  return (
    <div>
      <span>{authStatus}</span>
      <span>{isAuthenticated ? "Authenticated" : "Signed out"}</span>
      <button onClick={() => login("user@example.com", "secret123")}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
      <button onClick={retryStartup}>Retry</button>
      <button disabled={!isAuthenticated} onClick={() => fetchProjects()}>
        Load projects
      </button>
    </div>
  );
}


function renderProvider() {
  return render(
    <AuthProvider>
      <AuthHarness />
    </AuthProvider>
  );
}


describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("restores a session in memory and removes legacy stored tokens", async () => {
    localStorage.setItem("token", "legacy-local");
    sessionStorage.setItem("token", "legacy-session");
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse(session("restored-token")));
      }
      return Promise.resolve(jsonResponse({ projects: [] }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    renderProvider();

    expect(screen.getByText("initializing")).toBeInTheDocument();
    expect(await screen.findByText("Authenticated")).toBeInTheDocument();
    expect(localStorage.getItem("token")).toBeNull();
    expect(sessionStorage.getItem("token")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Load projects" }));
    const projectCall = fetchMock.mock.calls.find(([url]) =>
      url.endsWith("/projects")
    );
    expect(projectCall[1].headers.Authorization).toBe(
      "Bearer restored-token"
    );
  });

  it("settles unauthenticated without an expiry notice when startup has no session", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve(
          url.endsWith("/auth/csrf")
            ? jsonResponse({ csrf_token: "csrf" })
            : jsonResponse({ detail: "Invalid credentials" }, 401)
        )
      )
    );

    renderProvider();

    expect(await screen.findByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("Signed out")).toBeInTheDocument();
  });

  it("keeps a successful login memory-only", async () => {
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse({}, 401));
      }
      if (url.endsWith("/auth/login")) {
        return Promise.resolve(jsonResponse(session("login-token")));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderProvider();
    await screen.findByText("unauthenticated");

    await user.click(screen.getByRole("button", { name: "Login" }));

    expect(await screen.findByText("Authenticated")).toBeInTheDocument();
    expect(localStorage.getItem("token")).toBeNull();
    expect(sessionStorage.getItem("token")).toBeNull();
  });

  it("offers retry after a startup network failure", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockImplementation((url) =>
        Promise.resolve(
          url.endsWith("/auth/csrf")
            ? jsonResponse({ csrf_token: "csrf" })
            : jsonResponse(session())
        )
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderProvider();
    await screen.findByText("error");

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Authenticated")).toBeInTheDocument();
  });

  it("clears memory immediately and calls the protected logout endpoint", async () => {
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse(session()));
      }
      return Promise.resolve(jsonResponse({ message: "Logged out" }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderProvider();
    await screen.findByText("Authenticated");

    await user.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() =>
      expect(screen.getByText("unauthenticated")).toBeInTheDocument()
    );
    expect(
      fetchMock.mock.calls.some(([url]) => url.endsWith("/auth/logout"))
    ).toBe(true);
  });

  it("stays signed out when the logout request fails", async () => {
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(jsonResponse({ csrf_token: "csrf" }));
      }
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(jsonResponse(session()));
      }
      if (url.endsWith("/auth/logout")) {
        return Promise.reject(new TypeError("offline"));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderProvider();
    await screen.findByText("Authenticated");

    await user.click(screen.getByRole("button", { name: "Logout" }));

    expect(await screen.findByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("Signed out")).toBeInTheDocument();
  });

  it("deduplicates startup restoration under React Strict Mode", async () => {
    const fetchMock = vi.fn((url) =>
      Promise.resolve(
        url.endsWith("/auth/csrf")
          ? jsonResponse({ csrf_token: "csrf" })
          : jsonResponse(session())
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <StrictMode>
        <AuthProvider>
          <AuthHarness />
        </AuthProvider>
      </StrictMode>
    );

    expect(await screen.findByText("Authenticated")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))
    ).toHaveLength(1);
  });

  it("signs out when another tab broadcasts logout", async () => {
    let messageListener;
    class TestBroadcastChannel {
      addEventListener(_type, listener) {
        messageListener = listener;
      }
      postMessage() {}
      close() {}
    }
    vi.stubGlobal("BroadcastChannel", TestBroadcastChannel);
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve(
          url.endsWith("/auth/csrf")
            ? jsonResponse({ csrf_token: "csrf" })
            : jsonResponse(session())
        )
      )
    );
    renderProvider();
    await screen.findByText("Authenticated");

    act(() => messageListener({ data: { type: "logout" } }));

    expect(screen.getByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("Signed out")).toBeInTheDocument();
  });
});
