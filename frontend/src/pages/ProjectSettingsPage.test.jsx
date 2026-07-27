import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  listAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  downloadAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
}));

import ProjectSettingsPage from "./ProjectSettingsPage";
import { listAttachments } from "../services/api";


function attachment(id, filename) {
  return {
    id,
    original_filename: filename,
    mime_type: "application/pdf",
    size_bytes: 2048,
    created_at: "2026-07-26T12:00:00Z",
  };
}


function pageProps(overrides = {}) {
  return {
    projectId: 1,
    projectName: "North Ridge",
    projectCompanies: [],
    companyName: "",
    companyTrade: "",
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onCreate: vi.fn(),
    onNameChange: vi.fn(),
    onTradeChange: vi.fn(),
    onAttachmentError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectSettingsPage attachments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachments.mockResolvedValue({ attachments: [] });
  });

  it("does not mount or request documents without a persisted project", async () => {
    render(<ProjectSettingsPage {...pageProps({ projectId: null })} />);

    expect(
      screen.queryByRole("heading", { name: "Project Documents" })
    ).not.toBeInTheDocument();
    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(listAttachments).not.toHaveBeenCalled();
  });

  it("mounts one upload-and-delete panel for the selected project", async () => {
    listAttachments.mockResolvedValue({
      attachments: [attachment(11, "contract.pdf")],
    });

    render(<ProjectSettingsPage {...pageProps()} />);

    expect(
      screen.getByRole("heading", { name: "Project Documents" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/choose files/i)).toBeEnabled();
    expect(
      await screen.findByRole("button", { name: "Delete contract.pdf" })
    ).toBeEnabled();
    expect(listAttachments).toHaveBeenCalledTimes(1);
    expect(listAttachments).toHaveBeenCalledWith(
      1,
      "project",
      1,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("clears prior project files immediately when the identity changes", async () => {
    let resolveSecondProject;
    listAttachments.mockImplementation((projectId) => {
      if (projectId === 1) {
        return Promise.resolve({
          attachments: [attachment(11, "north-ridge.pdf")],
        });
      }
      return new Promise((resolve) => {
        resolveSecondProject = resolve;
      });
    });

    const { rerender } = render(
      <ProjectSettingsPage {...pageProps()} />
    );
    expect(await screen.findByText("north-ridge.pdf")).toBeInTheDocument();

    rerender(
      <ProjectSettingsPage
        {...pageProps({
          projectId: 2,
          projectName: "Desert View",
        })}
      />
    );

    expect(screen.queryByText("north-ridge.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("Loading attachments...")).toBeInTheDocument();
    await waitFor(() => expect(listAttachments).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveSecondProject({
        attachments: [attachment(22, "desert-view.pdf")],
      });
    });
    expect(await screen.findByText("desert-view.pdf")).toBeInTheDocument();
  });

  it("rejects a stale project response and reports failures globally", async () => {
    let resolveFirstProject;
    const onAttachmentError = vi.fn();
    listAttachments.mockImplementation((projectId) => {
      if (projectId === 1) {
        return new Promise((resolve) => {
          resolveFirstProject = resolve;
        });
      }
      return Promise.reject(new Error("Storage is unavailable"));
    });

    const { rerender } = render(
      <ProjectSettingsPage
        {...pageProps({ onAttachmentError })}
      />
    );
    await waitFor(() => expect(listAttachments).toHaveBeenCalledTimes(1));

    rerender(
      <ProjectSettingsPage
        {...pageProps({
          projectId: 2,
          projectName: "Desert View",
          onAttachmentError,
        })}
      />
    );

    expect(
      await screen.findByText("Storage is unavailable")
    ).toBeInTheDocument();
    expect(onAttachmentError).toHaveBeenCalledWith(
      "Unable to load attachments",
      expect.any(Error)
    );
    expect(screen.getByRole("button", { name: "Add Company" })).toBeEnabled();

    await act(async () => {
      resolveFirstProject({
        attachments: [attachment(11, "stale-project.pdf")],
      });
    });
    expect(screen.queryByText("stale-project.pdf")).not.toBeInTheDocument();
  });
});
