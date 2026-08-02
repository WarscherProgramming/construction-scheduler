import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDocumentsPage from "./ProjectDocumentsPage";


const useDocumentExplorerMock = vi.hoisted(() => vi.fn());
const relationshipPanelMock = vi.hoisted(() => vi.fn());
const useDocumentExtractionMock = vi.hoisted(() => vi.fn());
const extractionReprocessMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks/useDocumentExplorer", () => ({
  default: useDocumentExplorerMock,
}));
vi.mock("../components/relationships/RelationshipPanel", () => ({
  default: (props) => {
    relationshipPanelMock(props);
    return (
      <section aria-label={props.title}>
        <h2>{props.title}</h2>
      </section>
    );
  },
}));
vi.mock("../hooks/useDocumentExtraction", () => ({
  default: useDocumentExtractionMock,
}));


const FOLDER = {
  id: 2,
  name: "Drawings",
  parent_folder_id: null,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-30T12:00:00Z",
  child_folder_count: 1,
  document_count: 1,
};

const DOCUMENT = {
  id: 11,
  folder_id: null,
  display_name: "Issued Plans",
  original_filename: "issued-plans.pdf",
  extension: ".pdf",
  mime_type: "application/pdf",
  size_bytes: 1536,
  document_type: "Drawing",
  status: "Active",
  version: 1,
  created_at: "2026-07-30T12:00:00Z",
  updated_at: "2026-07-30T13:00:00Z",
  extraction: {
    status: "completed",
    extraction_method: "embedded_text",
    page_count: 2,
    pages_processed: 2,
    searchable: true,
    retry_eligible: true,
  },
};

const EXPLORER = {
  project_id: 1,
  current_folder: null,
  breadcrumbs: [],
  folders: [FOLDER],
  documents: [DOCUMENT],
  pagination: {
    limit: 50,
    offset: 0,
    total: 51,
    has_more: true,
  },
};

let hookState;


function pageProps(overrides = {}) {
  return {
    projectId: 1,
    projectName: "Riverside",
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRequestError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectDocumentsPage", () => {
  beforeEach(() => {
    hookState = {
      explorer: EXPLORER,
      folderTree: [
        FOLDER,
        {
          ...FOLDER,
          id: 3,
          name: "Issued",
          parent_folder_id: 2,
          document_count: 0,
        },
      ],
      recentDocuments: [DOCUMENT],
      query: {
        folderId: null,
        search: "",
        documentType: "",
        mimeType: "",
        extension: "",
        sort: "name",
        order: "asc",
        limit: 50,
        offset: 0,
      },
      isLoading: false,
      isNavigationLoading: false,
      error: null,
      operationError: null,
      isCreatingFolder: false,
      isUploading: false,
      uploadResults: [],
      failedUploadCount: 0,
      deletingIds: [],
      downloadingIds: [],
      updateQuery: vi.fn(),
      refresh: vi.fn(),
      uploadFiles: vi.fn(),
      retryFailedUploads: vi.fn(),
      createCurrentFolder: vi.fn().mockResolvedValue(true),
      removeDocument: vi.fn().mockResolvedValue(true),
      download: vi.fn(),
      clearOperationError: vi.fn(),
    };
    useDocumentExplorerMock.mockReset();
    useDocumentExplorerMock.mockImplementation(() => hookState);
    relationshipPanelMock.mockClear();
    useDocumentExtractionMock.mockReset();
    useDocumentExtractionMock.mockImplementation(({ initialExtraction }) => ({
      extraction: initialExtraction,
      error: null,
      isLoading: false,
      isReprocessing: false,
      reprocess: extractionReprocessMock.mockResolvedValue(true),
    }));
    extractionReprocessMock.mockClear();
  });

  it("renders the root, folder tree, document metadata, and recent files", () => {
    render(<ProjectDocumentsPage {...pageProps()} />);

    expect(
      screen.getByRole("heading", { name: "Project Documents", level: 1 })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Document location" })
    ).toHaveTextContent("Project root");
    expect(screen.getByRole("table")).toHaveTextContent("Drawings");
    expect(screen.getByRole("table")).toHaveTextContent("Issued Plans");
    expect(screen.getByRole("table")).toHaveTextContent("PDF");
    expect(
      screen.getByRole("heading", { name: "Recent Documents" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("Issued Plans").length).toBeGreaterThan(1);
  });

  it("shows initial, empty-folder, and no-search-results states", () => {
    hookState.isLoading = true;
    hookState.explorer = null;
    const view = render(<ProjectDocumentsPage {...pageProps()} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading documents"
    );

    hookState.isLoading = false;
    hookState.explorer = {
      ...EXPLORER,
      folders: [],
      documents: [],
      pagination: { ...EXPLORER.pagination, total: 0, has_more: false },
    };
    view.rerender(<ProjectDocumentsPage {...pageProps()} />);
    expect(screen.getByText("This folder is empty.")).toBeInTheDocument();

    hookState.query = { ...hookState.query, search: "missing" };
    view.rerender(<ProjectDocumentsPage {...pageProps()} />);
    expect(
      screen.getByText("No documents match this search.")
    ).toBeInTheDocument();
  });

  it("navigates folders and breadcrumbs with keyboard-accessible controls", async () => {
    const user = userEvent.setup();
    hookState.explorer = {
      ...EXPLORER,
      current_folder: FOLDER,
      breadcrumbs: [FOLDER],
    };
    hookState.query = { ...hookState.query, folderId: 2 };
    render(<ProjectDocumentsPage {...pageProps()} />);

    await user.click(
      screen.getByRole("button", { name: "Browse" })
    );
    const folderTree = screen.getByRole("navigation", {
      name: "Folder tree",
    });
    expect(
      within(folderTree).getByRole("button", { name: /Issued/ })
    ).toBeVisible();
    await user.click(
      within(folderTree).getByRole("button", { name: /Issued/ })
    );
    expect(hookState.updateQuery).toHaveBeenCalledWith({ folderId: 3 });

    const breadcrumbs = screen.getByRole("navigation", {
      name: "Document location",
    });
    const breadcrumb = within(breadcrumbs).getByRole("button", {
      name: "Drawings",
    });
    expect(breadcrumb).toHaveAttribute("aria-current", "location");
    await user.click(
      within(breadcrumbs).getByRole("button", { name: "Project root" })
    );
    expect(hookState.updateQuery).toHaveBeenCalledWith({ folderId: null });
  });

  it("searches, clears, filters, sorts, and changes pages", async () => {
    const user = userEvent.setup();
    render(<ProjectDocumentsPage {...pageProps()} />);

    const search = screen.getByRole("searchbox", {
      name: "Search document metadata",
    });
    await user.type(search, "issued");
    await user.click(screen.getByRole("button", { name: "Search documents" }));
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      search: "issued",
    });

    await user.selectOptions(screen.getByLabelText("Type"), "Drawing");
    await user.selectOptions(screen.getByLabelText("Format"), ".pdf");
    await user.selectOptions(
      screen.getByLabelText("Sort"),
      "updated_at:desc"
    );
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      documentType: "Drawing",
    });
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      extension: ".pdf",
    });
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      sort: "updated_at",
      order: "desc",
    });

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(hookState.updateQuery).toHaveBeenCalledWith({ offset: 50 });
  });

  it("creates a folder, reports duplicate failure, and restores focus", async () => {
    const user = userEvent.setup();
    render(<ProjectDocumentsPage {...pageProps()} />);

    await user.click(screen.getByRole("button", { name: "New Folder" }));
    const input = await screen.findByLabelText("Folder name");
    await user.type(input, " Coordination ");
    await user.click(screen.getByRole("button", { name: "Create Folder" }));

    expect(hookState.createCurrentFolder).toHaveBeenCalledWith(
      " Coordination "
    );
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Project root" })
      ).toHaveFocus()
    );

    hookState.createCurrentFolder.mockResolvedValueOnce(false);
    await user.click(screen.getByRole("button", { name: "New Folder" }));
    const retryInput = await screen.findByLabelText("Folder name");
    await user.type(retryInput, "Drawings");
    await user.click(screen.getByRole("button", { name: "Create Folder" }));
    await waitFor(() => expect(retryInput).toHaveFocus());
  });

  it("supports picker, drag-and-drop, partial results, and retry", async () => {
    const user = userEvent.setup();
    hookState.uploadResults = [
      {
        filename: "plans.pdf",
        status: "success",
        message: "Uploaded",
      },
      {
        filename: "large.pdf",
        status: "error",
        message: "Upload failed",
      },
    ];
    hookState.failedUploadCount = 1;
    render(<ProjectDocumentsPage {...pageProps()} />);

    const input = screen.getByLabelText("Choose documents to upload");
    const pickerFiles = [new File(["%PDF"], "plans.pdf")];
    fireEvent.change(input, { target: { files: pickerFiles } });
    expect(hookState.uploadFiles).toHaveBeenCalledWith(pickerFiles);

    const dropZone = screen.getByLabelText("Document upload area");
    const droppedFiles = [new File(["%PDF"], "field.pdf")];
    const drop = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(drop, "dataTransfer", {
      value: { types: ["Files"], files: droppedFiles },
    });
    fireEvent(dropZone, drop);
    expect(drop.defaultPrevented).toBe(true);
    expect(hookState.uploadFiles).toHaveBeenCalledWith(droppedFiles);
    expect(screen.getByText("Upload failed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry Failed" }));
    expect(hookState.retryFailedUploads).toHaveBeenCalledOnce();
  });

  it("opens metadata details, downloads, closes with Escape, and restores focus", async () => {
    const user = userEvent.setup();
    const view = render(<ProjectDocumentsPage {...pageProps()} />);
    const detailsButton = screen.getByRole("button", {
      name: "View details for Issued Plans",
    });

    await user.click(detailsButton);
    const dialog = screen.getByRole("dialog", { name: "Issued Plans" });
    expect(dialog).toHaveTextContent("issued-plans.pdf");
    expect(dialog).toHaveTextContent("application/pdf");
    expect(dialog).toHaveTextContent("1.5 KB");
    expect(dialog).not.toHaveTextContent(/storage_key|provider|bucket/i);

    await user.click(
      screen.getByRole("button", { name: "Download" })
    );
    expect(hookState.download).toHaveBeenCalledWith(DOCUMENT);

    hookState.downloadingIds = [DOCUMENT.id];
    view.rerender(<ProjectDocumentsPage {...pageProps()} />);
    expect(
      screen.getByRole("button", { name: "Downloading..." })
    ).toBeDisabled();

    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(detailsButton).toHaveFocus();
  });

  it("opens one document relationship panel from metadata details", async () => {
    const user = userEvent.setup();
    const props = pageProps();
    render(<ProjectDocumentsPage {...props} />);
    expect(relationshipPanelMock).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "View details for Issued Plans" })
    );
    await user.click(screen.getByRole("button", { name: "Relationships" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Issued Plans Relationships",
      })
    ).toBeInTheDocument();
    expect(relationshipPanelMock).toHaveBeenCalledOnce();
    expect(relationshipPanelMock).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 1,
        entityType: "document",
        entityId: 11,
        onNavigate: props.onNavigate,
        onError: props.onRequestError,
      })
    );
  });

  it("shows bundled extraction state and navigates to project search", async () => {
    const user = userEvent.setup();
    const page = pageProps();
    render(<ProjectDocumentsPage {...page} />);
    expect(screen.getByRole("table")).toHaveTextContent("Searchable");
    await user.click(
      screen.getByRole("button", { name: "View details for Issued Plans" })
    );
    expect(screen.getByRole("dialog")).toHaveTextContent("Embedded PDF text");
    expect(useDocumentExtractionMock).toHaveBeenCalledWith(
      expect.objectContaining({ load: false, documentId: 11 })
    );
    await user.click(screen.getByRole("button", { name: "Open Search" }));
    expect(page.onNavigate).toHaveBeenCalledWith(
      "projectDocumentSearch",
      1
    );
  });

  it("confirms replacement before reprocessing searchable text", async () => {
    const user = userEvent.setup();
    render(<ProjectDocumentsPage {...pageProps()} />);
    await user.click(
      screen.getByRole("button", { name: "View details for Issued Plans" })
    );
    await user.click(screen.getByRole("button", { name: "Reprocess Text" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Current search results remain available"
    );
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: "Reprocess Text",
      })
    );
    expect(extractionReprocessMock).toHaveBeenCalledOnce();
  });

  it("confirms soft deletion, prevents repeated submission, and keeps failures visible", async () => {
    const user = userEvent.setup();
    const pendingDelete = new Promise(() => {});
    hookState.removeDocument.mockReturnValueOnce(pendingDelete);
    const view = render(<ProjectDocumentsPage {...pageProps()} />);

    await user.click(
      screen.getByRole("button", { name: "Remove Issued Plans" })
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "It will not be permanently erased."
    );
    await user.click(
      screen.getByRole("button", { name: "Remove Document" })
    );
    expect(hookState.removeDocument).toHaveBeenCalledTimes(1);

    hookState.deletingIds = [DOCUMENT.id];
    view.rerender(<ProjectDocumentsPage {...pageProps()} />);
    expect(
      screen.getByRole("button", { name: "Removing..." })
    ).toBeDisabled();
  });

  it.each([
    [403, "do not have access"],
    [404, "no longer available"],
    [429, "temporarily limited"],
    [0, "Unable to connect"],
  ])("renders safe explorer failure state for status %s", (status, message) => {
    hookState.explorer = null;
    hookState.error = Object.assign(
      new Error(status === 0 ? "Unable to connect" : "Request failed"),
      { status }
    );
    render(<ProjectDocumentsPage {...pageProps()} />);

    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
});
