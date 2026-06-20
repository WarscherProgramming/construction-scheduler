import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import NewTaskInput from "./NewTaskInput";


describe("NewTaskInput", () => {
  it("saves once with Enter even when focus later leaves the input", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);

    render(
      <NewTaskInput
        value="Mobilization"
        onChange={vi.fn()}
        onSave={onSave}
        onCancel={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText("New task name"), "{enter}");
    await user.tab();

    expect(onSave).toHaveBeenCalledOnce();
  });

  it("cancels with Escape without saving", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onCancel = vi.fn();

    render(
      <NewTaskInput
        value="Mobilization"
        onChange={vi.fn()}
        onSave={onSave}
        onCancel={onCancel}
      />
    );

    await user.type(screen.getByLabelText("New task name"), "{escape}");

    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSave).not.toHaveBeenCalled();
  });
});
