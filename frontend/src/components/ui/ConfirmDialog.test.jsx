import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ConfirmDialog from "./ConfirmDialog";

const baseProps = {
  open: true,
  title: "Delete this task?",
  message: "This action cannot be undone.",
  confirmLabel: "Delete",
  destructive: true,
};

describe("ConfirmDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <ConfirmDialog
        {...baseProps}
        open={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("exposes an accessible alertdialog and focuses Cancel first", () => {
    render(
      <ConfirmDialog {...baseProps} onConfirm={vi.fn()} onCancel={vi.fn()} />
    );

    const dialog = screen.getByRole("alertdialog", {
      name: "Delete this task?",
    });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveTextContent("This action cannot be undone.");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
  });

  it("runs the confirm action", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();

    render(
      <ConfirmDialog {...baseProps} onConfirm={onConfirm} onCancel={vi.fn()} />
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("cancels with the Cancel button and with Escape", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(
      <ConfirmDialog {...baseProps} onConfirm={vi.fn()} onCancel={onCancel} />
    );

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.keyboard("{Escape}");

    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  it("traps Tab focus inside the dialog", async () => {
    const user = userEvent.setup();

    render(
      <ConfirmDialog {...baseProps} onConfirm={vi.fn()} onCancel={vi.fn()} />
    );

    const cancel = screen.getByRole("button", { name: "Cancel" });
    const confirm = screen.getByRole("button", { name: "Delete" });

    expect(cancel).toHaveFocus();
    await user.tab();
    expect(confirm).toHaveFocus();
    await user.tab();
    expect(cancel).toHaveFocus();
    await user.tab({ shift: true });
    expect(confirm).toHaveFocus();
  });
});
