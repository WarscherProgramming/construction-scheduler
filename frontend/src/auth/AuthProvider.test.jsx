import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthProvider from "./AuthProvider";
import { useAuth } from "./authContext";


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
});
