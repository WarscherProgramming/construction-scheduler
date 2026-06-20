import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthProvider from "./AuthProvider";
import { useAuth } from "./authContext";
import { fetchProjects } from "../services/api";


function AuthHarness() {
  const { isAuthenticated, login, logout } = useAuth();

  return (
    <div>
      <span>{isAuthenticated ? "Authenticated" : "Signed out"}</span>
      <button onClick={() => login("user@example.com", "secret123")}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

function InitialRequestHarness() {
  const { isAuthenticated } = useAuth();

  return (
    <div>
      <span>{isAuthenticated ? "Authenticated" : "Signed out"}</span>
      <button
        disabled={!isAuthenticated}
        onClick={async () => {
          try {
            await fetchProjects();
          } catch {
            // Authentication state is the behavior under test.
          }
        }}
      >
        Load projects
      </button>
    </div>
  );
}


describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("persists a successful login and clears it on logout", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: "test-token",
            token_type: "bearer",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        )
      )
    );

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    expect(screen.getByText("Signed out")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Login" }));

    expect(await screen.findByText("Authenticated")).toBeInTheDocument();
    expect(localStorage.getItem("token")).toBe("test-token");

    await user.click(screen.getByRole("button", { name: "Logout" }));

    expect(screen.getByText("Signed out")).toBeInTheDocument();
    expect(localStorage.getItem("token")).toBeNull();
  });

  it("attaches a restored token to the first authenticated request", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "restored-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ projects: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <InitialRequestHarness />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: "Load projects" }));

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer restored-token"
    );
  });

  it("clears an invalid restored token after a 401 response", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "expired-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Invalid token" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    render(
      <AuthProvider>
        <InitialRequestHarness />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: "Load projects" }));

    expect(await screen.findByText("Signed out")).toBeInTheDocument();
    expect(localStorage.getItem("token")).toBeNull();
  });
});
