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

  it("filters records by search text and announces the result count", async () => {
    const user = userEvent.setup();

    render(
      <DailyLogsPage
        projectName="North Ridge"
        dailyLogs={[
          {
            id: 1,
            date: "2026-06-20",
            company: "Desert Concrete",
            manpower: 8,
            notes: "North pour complete",
          },
          {
            id: 2,
            date: "2026-06-19",
            company: "Valley Electric",
            manpower: 4,
            notes: "Panel work underway",
          },
        ]}
        projectCompanies={[
          { id: 1, name: "Desert Concrete" },
          { id: 2, name: "Valley Electric" },
        ]}
        logDate="2026-06-20"
        logCompany=""
        logManpower=""
        logNotes=""
        formatDate={(value) => value}
        onBack={vi.fn()}
        onRefresh={vi.fn()}
        onCreate={vi.fn()}
        onDateChange={vi.fn()}
        onCompanyChange={vi.fn()}
        onManpowerChange={vi.fn()}
        onNotesChange={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText("Search"), "panel");

    expect(screen.getByText("Panel work underway")).toBeInTheDocument();
    expect(screen.queryByText("North pour complete")).not.toBeInTheDocument();
    expect(screen.getByText("1 record")).toBeInTheDocument();
  });

  it("disables save and refresh actions while they are running", () => {
    render(
      <DailyLogsPage
        projectName="North Ridge"
        dailyLogs={[]}
        projectCompanies={[]}
        logDate="2026-06-20"
        logCompany=""
        logManpower=""
        logNotes=""
        formatDate={(value) => value}
        onBack={vi.fn()}
        onRefresh={vi.fn()}
        onCreate={vi.fn()}
        onDateChange={vi.fn()}
        onCompanyChange={vi.fn()}
        onManpowerChange={vi.fn()}
        onNotesChange={vi.fn()}
        isCreating
        isRefreshing
      />
    );

    expect(
      screen.getByRole("button", { name: "Saving daily log…" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Refreshing logs…" })
    ).toBeDisabled();
  });
});
