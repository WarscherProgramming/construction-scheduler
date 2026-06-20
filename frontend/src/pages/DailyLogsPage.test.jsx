import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DailyLogsPage from "./DailyLogsPage";


describe("DailyLogsPage", () => {
  it("labels required fields and submits the form", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();

    render(
      <DailyLogsPage
        projectName="North Ridge"
        dailyLogs={[]}
        projectCompanies={[{ id: 1, name: "Desert Concrete" }]}
        logDate="2026-06-20"
        logCompany="Desert Concrete"
        logManpower="8"
        logNotes=""
        formatDate={(value) => value}
        onBack={vi.fn()}
        onRefresh={vi.fn()}
        onCreate={onCreate}
        onDateChange={vi.fn()}
        onCompanyChange={vi.fn()}
        onManpowerChange={vi.fn()}
        onNotesChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Date *")).toBeRequired();
    expect(screen.getByLabelText("Company *")).toBeRequired();
    expect(screen.getByLabelText("Manpower *")).toBeRequired();

    await user.click(screen.getByRole("button", { name: "Save Daily Log" }));

    expect(onCreate).toHaveBeenCalledOnce();
  });
});
