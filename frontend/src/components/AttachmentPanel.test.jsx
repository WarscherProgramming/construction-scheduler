import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AttachmentPanel from "./AttachmentPanel";


const useAttachmentsMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks/useAttachments", () => ({
  default: useAttachmentsMock,
}));


const ATTACHMENT = {
  id: 11,
  original_filename: "plans.pdf",
  mime_type: "application/pdf",
  size_bytes: 1_572_864,
  created_at: "2026-07-26T12:00:00Z",
};

let hookState;


function renderPanel(props = {}) {
  return render(
    <AttachmentPanel
      projectId={1}
      parentType="project"
      parentId={1}
      {...props}
    />
  );
}


describe("AttachmentPanel", () => {
  beforeEach(() => {
    hookState = {
      attachments: [],
      isLoading: false,
      isUploading: false,
      uploadingFilename: "",
      uploadResults: [],
      deletingIds: [],
      downloadingIds: [],
      error: null,
      refresh: vi.fn(),
      uploadFiles: vi.fn(),
      downloadAttachment: vi.fn(),
      deleteAttachment: vi.fn().mockResolvedValue(true),
      clearError: vi.fn(),
    };
    useAttachmentsMock.mockReset();
    useAttachmentsMock.mockImplementation(() => hookState);
  });

  it("does not render active UI or fetch when the parent lacks an ID", () => {
    const { container } = renderPanel({ parentId: null });

    expect(container).toBeEmptyDOMElement();
    expect(useAttachmentsMock).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: false })
    );
  });

  it("shows the title, count, and reports count changes", () => {
    hookState.attachments = [ATTACHMENT];
    const onCountChange = vi.fn();
    renderPanel({
      title: "Project documents",
      onCountChange,
    });

    expect(
      screen.getByRole("heading", { name: "Project documents" })
    ).toBeInTheDocument();
    expect(screen.getByText("1 file")).toBeInTheDocument();
    expect(onCountChange).toHaveBeenCalledWith(1);
  });

  it("renders panel-level loading and empty states", () => {
    hookState.isLoading = true;
    const view = renderPanel();
    expect(screen.getByText("Loading attachments...")).toBeInTheDocument();

    hookState.isLoading = false;
    view.rerender(
      <AttachmentPanel
        projectId={1}
        parentType="project"
        parentId={1}
      />
    );
    expect(screen.getByText("No attachments yet.")).toBeInTheDocument();
  });

  it("renders semantic file metadata and filename-specific actions", () => {
    hookState.attachments = [
      ATTACHMENT,
      {
        id: 12,
        original_filename: "field report.docx",
        mime_type:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes: 512,
        created_at: "2026-07-26T12:00:00Z",
      },
    ];
    renderPanel();

    expect(screen.getByRole("list", { name: "Attachments files" })).toBe(
      screen.getByText("plans.pdf").closest("ul")
    );
    expect(screen.getByText("plans.pdf").nextElementSibling).toHaveTextContent(
      "PDF · 1.5 MB"
    );
    expect(
      screen.getByText("field report.docx").nextElementSibling
    ).toHaveTextContent("Word document · 512 B");
    expect(
      screen.getByRole("button", { name: "Preview plans.pdf" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Download field report.docx",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete plans.pdf" })
    ).toBeInTheDocument();
  });

  it("shows a retryable list error and dismiss action", async () => {
    const user = userEvent.setup();
    hookState.error = {
      operation: "list",
      message: "Attachments are unavailable",
    };
    renderPanel();

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Attachments are unavailable"
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await user.click(
      screen.getByRole("button", { name: "Dismiss attachment error" })
    );
    expect(hookState.refresh).toHaveBeenCalledTimes(1);
    expect(hookState.clearError).toHaveBeenCalledTimes(1);
  });

  it("associates the file input and uploads multiple selected files", () => {
    renderPanel();
    const input = screen.getByLabelText(/Choose files/i);
    const files = [
      new File(["one"], "one.pdf"),
      new File(["two"], "two.pdf"),
    ];

    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute("multiple");
    fireEvent.change(input, { target: { files } });

    expect(hookState.uploadFiles).toHaveBeenCalledWith(files);
  });

  it("supports file drops, prevents file navigation, and ignores non-files", () => {
    renderPanel();
    const dropZone = screen.getByRole("button", { name: /Choose files/i });
    const files = [new File(["one"], "one.pdf")];
    const fileDrop = new Event("drop", {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(fileDrop, "dataTransfer", {
      value: { types: ["Files"], files },
    });

    fireEvent(dropZone, fileDrop);
    expect(fileDrop.defaultPrevented).toBe(true);
    expect(hookState.uploadFiles).toHaveBeenCalledWith(files);

    fireEvent.drop(dropZone, {
      dataTransfer: { types: ["text/plain"], files: [] },
    });
    expect(hookState.uploadFiles).toHaveBeenCalledTimes(1);
  });

  it("announces drag-over and per-file upload status", () => {
    hookState.isUploading = true;
    hookState.uploadingFilename = "plans.pdf";
    hookState.uploadResults = [
      {
        filename: "plans.pdf",
        status: "success",
        message: "Uploaded",
      },
      {
        filename: "large.pdf",
        status: "error",
        message: "Exceeds the limit",
      },
    ];
    renderPanel();

    expect(screen.getByRole("status")).toHaveTextContent(
      "Uploading plans.pdf"
    );
    expect(screen.getByRole("list", { name: "Upload results" })).toHaveTextContent(
      "plans.pdfUploaded"
    );
    expect(screen.getByText("Exceeds the limit")).toBeInTheDocument();
  });

  it("opens the native picker from the keyboard-accessible drop zone", () => {
    renderPanel();
    const input = screen.getByLabelText(/Choose files/i);
    const click = vi.spyOn(input, "click").mockImplementation(() => {});
    const dropZone = screen.getByRole("button", { name: /Choose files/i });

    fireEvent.keyDown(dropZone, { key: "Enter" });
    fireEvent.keyDown(dropZone, { key: " " });

    expect(click).toHaveBeenCalledTimes(2);
  });

  it("dispatches authenticated download behavior through the hook", async () => {
    const user = userEvent.setup();
    hookState.attachments = [ATTACHMENT];
    renderPanel();

    await user.click(
      screen.getByRole("button", { name: "Preview plans.pdf" })
    );

    expect(hookState.downloadAttachment).toHaveBeenCalledWith(ATTACHMENT);
  });

  it("uses ConfirmDialog for deletion and cancel leaves the file unchanged", async () => {
    const user = userEvent.setup();
    hookState.attachments = [ATTACHMENT];
    renderPanel();

    await user.click(
      screen.getByRole("button", { name: "Delete plans.pdf" })
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Delete plans.pdf?"
    );
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(hookState.deleteAttachment).not.toHaveBeenCalled();
    expect(screen.getByText("plans.pdf")).toBeInTheDocument();
  });

  it("confirms deletion once and restores focus within the panel", async () => {
    const user = userEvent.setup();
    hookState.attachments = [ATTACHMENT];
    renderPanel();

    await user.click(
      screen.getByRole("button", { name: "Delete plans.pdf" })
    );
    await user.click(
      screen.getByRole("button", { name: "Delete", exact: true })
    );

    await waitFor(() =>
      expect(hookState.deleteAttachment).toHaveBeenCalledWith(ATTACHMENT)
    );
    expect(
      screen.getByRole("heading", { name: "Attachments" })
    ).toHaveFocus();
  });

  it("preserves the visible file when deletion fails", async () => {
    const user = userEvent.setup();
    hookState.attachments = [ATTACHMENT];
    hookState.deleteAttachment.mockResolvedValue(false);
    renderPanel();

    await user.click(
      screen.getByRole("button", { name: "Delete plans.pdf" })
    );
    await user.click(
      screen.getByRole("button", { name: "Delete", exact: true })
    );

    await waitFor(() =>
      expect(hookState.deleteAttachment).toHaveBeenCalledTimes(1)
    );
    expect(screen.getByText("plans.pdf")).toBeInTheDocument();
  });

  it("honors upload and delete permissions independently", () => {
    hookState.attachments = [ATTACHMENT];
    renderPanel({ canUpload: false, canDelete: false });

    expect(
      screen.queryByRole("button", { name: /Choose files/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Delete plans.pdf" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Preview plans.pdf" })
    ).toBeInTheDocument();
  });

  it("uses safe fallbacks for unknown files and invalid dates", () => {
    hookState.attachments = [
      {
        id: 20,
        original_filename: "",
        mime_type: "application/octet-stream",
        size_bytes: null,
        created_at: "invalid",
      },
    ];
    renderPanel();

    expect(screen.getByText("Attachment")).toBeInTheDocument();
    expect(
      screen.getByText("Attachment").nextElementSibling
    ).toHaveTextContent("File · 0 B · Date unavailable");
    expect(
      screen.getByRole("button", { name: "Download Attachment" })
    ).toBeInTheDocument();
  });
});
