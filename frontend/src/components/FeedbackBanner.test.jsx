import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import FeedbackBanner from "./FeedbackBanner";


describe("FeedbackBanner", () => {
  it("announces errors assertively and supports dismissal", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();

    render(
      <FeedbackBanner
        notice={{ id: 1, type: "error", message: "Daily log was not saved." }}
        onDismiss={onDismiss}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Daily log was not saved."
    );

    await user.click(
      screen.getByRole("button", { name: "Dismiss notification" })
    );

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("announces successful actions politely", () => {
    render(
      <FeedbackBanner
        notice={{ id: 2, type: "success", message: "Inspection saved." }}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByRole("status")).toHaveTextContent("Inspection saved.");
  });
});
