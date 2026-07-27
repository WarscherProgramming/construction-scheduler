import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  listAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  downloadAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
}));

import DailyLogsPage from "./DailyLogsPage";
import { listAttachments } from "../services/api";


function attachment(id, filename) {
  return {
    id,
    original_filename: filename,
    mime_type: "image/jpeg",
    size_bytes: 4096,
    created_at: "2026-07-26T12:00:00Z",
  };
}


function pageProps(overrides = {}) {
  return {
    projectId: 1,
    projectName: "North Ridge",
    dailyLogs: [
      {
        id: 10,
        date: "2026-06-20",
        company: "Desert Concrete",
        manpower: 8,
        notes: "North pour complete",
      },
      {
        id: 20,
        date: "2026-06-19",
        company: "Valley Electric",
        manpower: 4,
        notes: "Panel work underway",
      },
    ],
    projectCompanies: [
      { id: 1, name: "Desert Concrete" },
      { id: 2, name: "Valley Electric" },
    ],
    logDate: "2026-06-20",
    logCompany: "",
    logManpower: "",
    logNotes: "",
    formatDate: (value) => value,
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRefresh: vi.fn(),
    onCreate: vi.fn(),
    onDateChange: vi.fn(),
    onCompanyChange: vi.fn(),
    onManpowerChange: vi.fn(),
    onNotesChange: vi.fn(),
    onAttachmentError: vi.fn(),
    ...overrides,
  };
}


describe("DailyLogsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachments.mockResolvedValue({ attachments: [] });
  });

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

  it("does not request attachments for the creation form or closed logs", async () => {
    render(<DailyLogsPage {...pageProps()} />);

    expect(
      screen.queryByRole("heading", { name: "Daily Log Attachments" })
    ).not.toBeInTheDocument();
    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(listAttachments).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save Daily Log" })).toBeEnabled();
  });

  it("opens one persisted log attachment panel with accessible controls", async () => {
    const user = userEvent.setup();
    listAttachments.mockResolvedValue({
      attachments: [attachment(51, "site-photo.jpg")],
    });
    render(<DailyLogsPage {...pageProps()} />);

    const openButton = screen.getByRole("button", {
      name: "Attachments for daily log 2026-06-20 for Desert Concrete",
    });
    expect(openButton).toHaveAttribute("aria-expanded", "false");
    expect(openButton).toHaveAttribute(
      "aria-controls",
      "daily-log-attachments-10"
    );

    openButton.focus();
    await user.keyboard("{Enter}");

    expect(openButton).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("region", {
        name: "Attachments for daily log 2026-06-20 for Desert Concrete",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Daily Log Attachments" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/choose files/i)).toBeEnabled();
    expect(
      await screen.findByRole("button", { name: "Delete site-photo.jpg" })
    ).toBeEnabled();
    expect(listAttachments).toHaveBeenCalledTimes(1);
    expect(listAttachments).toHaveBeenCalledWith(
      1,
      "daily_log",
      10,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );

    await user.click(
      screen.getByRole("button", {
        name: "Close attachments for daily log 2026-06-20 for Desert Concrete",
      })
    );
    expect(
      screen.queryByRole("heading", { name: "Daily Log Attachments" })
    ).not.toBeInTheDocument();
  });

  it("replaces the active log and rejects the prior stale response", async () => {
    const user = userEvent.setup();
    let resolveFirstLog;
    listAttachments.mockImplementation((_projectId, _parentType, parentId) => {
      if (parentId === 10) {
        return new Promise((resolve) => {
          resolveFirstLog = resolve;
        });
      }
      return Promise.resolve({
        attachments: [attachment(52, "panel-ticket.jpg")],
      });
    });
    render(<DailyLogsPage {...pageProps()} />);

    await user.click(
      screen.getByRole("button", {
        name: "Attachments for daily log 2026-06-20 for Desert Concrete",
      })
    );
    await waitFor(() => expect(listAttachments).toHaveBeenCalledTimes(1));

    await user.click(
      screen.getByRole("button", {
        name: "Attachments for daily log 2026-06-19 for Valley Electric",
      })
    );
    expect(await screen.findByText("panel-ticket.jpg")).toBeInTheDocument();
    expect(listAttachments).toHaveBeenCalledTimes(2);

    await act(async () => {
      resolveFirstLog({
        attachments: [attachment(51, "stale-site-photo.jpg")],
      });
    });
    expect(screen.queryByText("stale-site-photo.jpg")).not.toBeInTheDocument();
    expect(
      screen.getByRole("region", {
        name: "Attachments for daily log 2026-06-19 for Valley Electric",
      })
    ).toBeInTheDocument();
  });

  it("closes the selected log when the project changes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <DailyLogsPage key={1} {...pageProps()} />
    );

    await user.click(
      screen.getByRole("button", {
        name: "Attachments for daily log 2026-06-20 for Desert Concrete",
      })
    );
    expect(
      screen.getByRole("heading", { name: "Daily Log Attachments" })
    ).toBeInTheDocument();

    rerender(
      <DailyLogsPage
        key={2}
        {...pageProps({
          projectId: 2,
          projectName: "Desert View",
          dailyLogs: [
            {
              id: 10,
              date: "2026-06-21",
              company: "Mesa Steel",
              manpower: 6,
              notes: "Steel delivery",
            },
          ],
        })}
      />
    );

    expect(
      screen.queryByRole("heading", { name: "Daily Log Attachments" })
    ).not.toBeInTheDocument();
    expect(listAttachments).toHaveBeenCalledTimes(1);
  });

  it("keeps Daily Log controls usable and reports attachment failures globally", async () => {
    const user = userEvent.setup();
    const requestError = new Error("Storage is unavailable");
    const onAttachmentError = vi.fn();
    listAttachments.mockRejectedValue(requestError);
    render(
      <DailyLogsPage
        {...pageProps({ onAttachmentError })}
      />
    );

    await user.click(
      screen.getByRole("button", {
        name: "Attachments for daily log 2026-06-20 for Desert Concrete",
      })
    );

    expect(
      await screen.findByText("Storage is unavailable")
    ).toBeInTheDocument();
    expect(onAttachmentError).toHaveBeenCalledWith(
      "Unable to load attachments",
      requestError
    );
    expect(screen.getByRole("button", { name: "Save Daily Log" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Refresh Logs" })).toBeEnabled();
  });
});
