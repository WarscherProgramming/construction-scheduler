import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AuthPage from "./AuthPage";


describe("AuthPage", () => {
  it("submits login credentials through controlled callbacks", async () => {
    const user = userEvent.setup();
    const onEmailChange = vi.fn();
    const onPasswordChange = vi.fn();
    const onLogin = vi.fn();

    const { rerender } = render(
      <AuthPage
        authMode="login"
        email=""
        password=""
        onEmailChange={onEmailChange}
        onPasswordChange={onPasswordChange}
        onLogin={onLogin}
        onRegister={vi.fn()}
        onToggleMode={vi.fn()}
      />
    );

    await user.type(screen.getByPlaceholderText("Email"), "user@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secret123");

    expect(onEmailChange).toHaveBeenLastCalledWith("m");
    expect(onPasswordChange).toHaveBeenLastCalledWith("3");

    rerender(
      <AuthPage
        authMode="login"
        email="user@example.com"
        password="secret123"
        onEmailChange={onEmailChange}
        onPasswordChange={onPasswordChange}
        onLogin={onLogin}
        onRegister={vi.fn()}
        onToggleMode={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: "Login" }));
    expect(onLogin).toHaveBeenCalledOnce();
  });

  it("switches account mode through the toggle action", async () => {
    const user = userEvent.setup();
    const onToggleMode = vi.fn();

    render(
      <AuthPage
        authMode="register"
        email=""
        password=""
        onEmailChange={vi.fn()}
        onPasswordChange={vi.fn()}
        onLogin={vi.fn()}
        onRegister={vi.fn()}
        onToggleMode={onToggleMode}
      />
    );

    await user.click(
      screen.getByRole("button", {
        name: "Already have an account? Login",
      })
    );

    expect(onToggleMode).toHaveBeenCalledOnce();
  });
});
