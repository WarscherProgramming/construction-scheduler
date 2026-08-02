import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDrawingViewerPage from "./ProjectDrawingViewerPage";


const useDrawingViewerMock = vi.hoisted(() => vi.fn());
const relationshipPanelMock = vi.hoisted(() => vi.fn());
const useDocumentExtractionMock = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useDrawingViewer", () => ({ default: useDrawingViewerMock }));
vi.mock("../hooks/useDocumentExtraction", () => ({
  default: useDocumentExtractionMock,
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
vi.mock("../utils/pdfViewer", () => ({
  PDF_ANNOTATION_MODE_DISABLED: 0,
  PDF_SEARCH_QUERY_MAX: 200,
  PDF_THUMBNAIL_RADIUS: 2,
  createPdfTextLayer: vi.fn(),
}));
vi.mock("../components/drawings/viewer/PdfCanvasViewport", () => ({
  default: ({ pageNumber, sheetLabel }) => (
    <div role="region" aria-label="Drawing PDF viewport" tabIndex="0">
      {sheetLabel}, page {pageNumber}
    </div>
  ),
}));
vi.mock("../components/drawings/viewer/DrawingThumbnailRail", () => ({
  default: ({ currentPage, onSelect }) => (
    <aside aria-label="PDF page list">
      <span>Current thumbnail {currentPage}</span>
      <button type="button" onClick={() => onSelect(2)}>Thumbnail page 2</button>
    </aside>
  ),
}));


const CURRENT_REVISION = {
  id: 30,
  drawing_sheet_id: 20,
  revision_code: "1",
  revision_date: "2026-08-01",
  description: "Issued for construction",
  sequence_number: 2,
  is_current: true,
  superseded_at: null,
  superseded_by_revision_id: null,
  original_filename: "A-101-r1.pdf",
  size_bytes: 2048,
  created_at: "2026-08-01T12:00:00Z",
  issue_ids: [50],
  document_id: 40,
};
const OLD_REVISION = {
  ...CURRENT_REVISION,
  id: 29,
  revision_code: "0",
  sequence_number: 1,
  is_current: false,
  superseded_at: "2026-08-01T12:00:00Z",
  superseded_by_revision_id: 30,
};
const SHEET = {
  id: 20,
  drawing_set_id: 10,
  drawing_set_name: "IFC",
  sheet_number: "A-101",
  title: "Floor Plan",
  discipline: "A",
};

let viewer;


function pageProps(overrides = {}) {
  return {
    projectId: 1,
    projectName: "Riverside",
    sheetId: 20,
    revisionId: 30,
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRequestError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectDrawingViewerPage", () => {
  beforeEach(() => {
    viewer = {
      sheet: SHEET,
      revision: CURRENT_REVISION,
      revisions: [CURRENT_REVISION, OLD_REVISION],
      previousSheet: {
        id: 19,
        current_revision: { id: 27 },
      },
      nextSheet: {
        id: 21,
        current_revision: { id: 31 },
      },
      pdfDocument: { numPages: 3 },
      pageCount: 3,
      currentPage: 1,
      setCurrentPage: vi.fn(),
      zoomMode: "fit-width",
      zoomPercent: 100,
      zoomIn: vi.fn(),
      zoomOut: vi.fn(),
      resetZoom: vi.fn(),
      fitWidth: vi.fn(),
      fitPage: vi.fn(),
      search: {
        query: "",
        matches: [],
        matchIndex: -1,
        isIndexing: false,
        hasText: null,
        error: "",
      },
      searchPdf: vi.fn(),
      moveSearchMatch: vi.fn(),
      clearSearch: vi.fn(),
      phase: "ready",
      error: null,
      retry: vi.fn(),
      canDownload: true,
      download: vi.fn(),
    };
    useDrawingViewerMock.mockReset();
    useDrawingViewerMock.mockImplementation(() => viewer);
    relationshipPanelMock.mockClear();
    useDocumentExtractionMock.mockReset();
    useDocumentExtractionMock.mockReturnValue({
      extraction: {
        status: "completed",
        extraction_method: "embedded_text",
        searchable: true,
      },
      isLoading: false,
      error: null,
      isReprocessing: false,
      reprocess: vi.fn(),
    });
  });

  it("displays safe sheet, revision, and page metadata with one h1", () => {
    render(<ProjectDrawingViewerPage {...pageProps()} />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "A-101 - Floor Plan" })).toBeInTheDocument();
    expect(screen.getAllByText(/Current Revision/)).not.toHaveLength(0);
    expect(screen.getByText("A - Architectural")).toBeInTheDocument();
    expect(screen.getByText("Issued for construction")).toBeInTheDocument();
    expect(screen.getByText(/depends on the uploaded source PDF/)).toBeInTheDocument();
  });

  it("supports page boundaries, direct entry, and thumbnail selection", async () => {
    const user = userEvent.setup();
    render(<ProjectDrawingViewerPage {...pageProps()} />);

    expect(screen.getByRole("button", { name: "First page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(viewer.setCurrentPage).toHaveBeenCalledWith(2);

    const input = screen.getByLabelText("Page");
    await user.clear(input);
    await user.type(input, "3");
    await user.click(screen.getByRole("button", { name: "Go" }));
    expect(viewer.setCurrentPage).toHaveBeenCalledWith(3);

    await user.click(screen.getByRole("button", { name: "Thumbnail page 2" }));
    expect(viewer.setCurrentPage).toHaveBeenCalledWith(2);
  });

  it("provides every zoom mode", async () => {
    const user = userEvent.setup();
    render(<ProjectDrawingViewerPage {...pageProps()} />);

    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    await user.click(screen.getByRole("button", { name: "Zoom out" }));
    await user.click(screen.getByRole("button", { name: "100%" }));
    await user.click(screen.getByRole("button", { name: "Fit Width" }));
    await user.click(screen.getByRole("button", { name: "Fit Page" }));
    expect(viewer.zoomIn).toHaveBeenCalledOnce();
    expect(viewer.zoomOut).toHaveBeenCalledOnce();
    expect(viewer.resetZoom).toHaveBeenCalledOnce();
    expect(viewer.fitWidth).toHaveBeenCalledOnce();
    expect(viewer.fitPage).toHaveBeenCalledOnce();
  });

  it("scopes page and zoom keyboard shortcuts to the workspace", () => {
    render(<ProjectDrawingViewerPage {...pageProps()} />);
    const workspace = screen.getByLabelText("Drawing viewer workspace");

    fireEvent.keyDown(workspace, { key: "ArrowRight" });
    fireEvent.keyDown(workspace, { key: "+" });
    fireEvent.keyDown(workspace, { key: "f" });
    expect(viewer.setCurrentPage).toHaveBeenCalledWith(2);
    expect(viewer.zoomIn).toHaveBeenCalledOnce();
    expect(viewer.fitWidth).toHaveBeenCalledOnce();
  });

  it("searches, reports matches, navigates results, and clears safely", async () => {
    const user = userEvent.setup();
    viewer.search = {
      ...viewer.search,
      query: "door",
      matches: [1, 2],
      matchIndex: 0,
      hasText: true,
    };
    render(<ProjectDrawingViewerPage {...pageProps()} />);

    expect(screen.getByText("1 of 2 matches")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next Match" }));
    await user.click(screen.getByRole("button", { name: "Previous Match" }));
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(viewer.moveSearchMatch).toHaveBeenNthCalledWith(1, 1);
    expect(viewer.moveSearchMatch).toHaveBeenNthCalledWith(2, -1);
    expect(viewer.clearSearch).toHaveBeenCalledOnce();
  });

  it("states when searchable text is unavailable", () => {
    viewer.search = { ...viewer.search, query: "note", hasText: false };
    render(<ProjectDrawingViewerPage {...pageProps()} />);
    expect(screen.getByText("Searchable text is not available for this revision.")).toBeInTheDocument();
  });

  it("distinguishes viewer search from project index status", async () => {
    const user = userEvent.setup();
    const page = pageProps();
    render(<ProjectDrawingViewerPage {...page} />);
    expect(screen.getByText("Current PDF embedded text")).toBeInTheDocument();
    expect(screen.getByText("Embedded PDF text")).toBeInTheDocument();
    expect(useDocumentExtractionMock).toHaveBeenCalledWith(
      expect.objectContaining({ projectId: 1, documentId: 40, load: true })
    );
    await user.click(screen.getByRole("button", { name: "Open Search" }));
    expect(page.onNavigate).toHaveBeenCalledWith(
      "projectDocumentSearch",
      1
    );
    expect(viewer.download).not.toHaveBeenCalled();
  });

  it("navigates exact revisions and adjacent sheets through safe IDs", async () => {
    const user = userEvent.setup();
    const props = pageProps();
    render(<ProjectDrawingViewerPage {...props} />);

    await user.selectOptions(screen.getByLabelText("Revision history"), "29");
    expect(props.onNavigate).toHaveBeenCalledWith("drawingViewer", 1, {
      sheetId: 20,
      revisionId: 29,
    });
    await user.click(screen.getByRole("button", { name: "View next drawing sheet" }));
    expect(props.onNavigate).toHaveBeenCalledWith("drawingViewer", 1, {
      sheetId: 21,
      revisionId: 31,
    });
  });

  it("loads revision relationships on demand without a PDF action", async () => {
    const user = userEvent.setup();
    const props = pageProps();
    const view = render(<ProjectDrawingViewerPage {...props} />);
    expect(relationshipPanelMock).not.toHaveBeenCalled();
    expect(viewer.download).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Relationships" }));
    expect(
      screen.getByRole("heading", { name: "Revision 1 Relationships" })
    ).toBeInTheDocument();
    expect(relationshipPanelMock).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 1,
        entityType: "drawing_revision",
        entityId: 30,
        onNavigate: props.onNavigate,
        onError: props.onRequestError,
      })
    );
    expect(viewer.download).not.toHaveBeenCalled();

    viewer = { ...viewer, revision: OLD_REVISION };
    view.rerender(
      <ProjectDrawingViewerPage {...pageProps({ revisionId: 29 })} />
    );
    expect(relationshipPanelMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        entityType: "drawing_revision",
        entityId: 29,
      })
    );
    expect(viewer.download).not.toHaveBeenCalled();
  });

  it("reuses the loaded PDF for download and returns to the register", async () => {
    const user = userEvent.setup();
    const props = pageProps();
    render(<ProjectDrawingViewerPage {...props} />);

    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await user.click(screen.getByRole("button", { name: "Drawing Register" }));
    expect(viewer.download).toHaveBeenCalledOnce();
    expect(props.onNavigate).toHaveBeenCalledWith("projectDrawings", 1);
  });

  it("shows distinct loading phases", () => {
    viewer.phase = "download";
    viewer.sheet = null;
    viewer.revision = null;
    render(<ProjectDrawingViewerPage {...pageProps()} />);
    expect(screen.getAllByText("Downloading authorized PDF...")).toHaveLength(2);
  });

  it("keeps metadata and authorized download available after a PDF error", async () => {
    const user = userEvent.setup();
    viewer.phase = "error";
    viewer.error = { message: "Password-protected or encrypted PDFs are not supported in the viewer." };
    render(<ProjectDrawingViewerPage {...pageProps()} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Password-protected");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(viewer.retry).toHaveBeenCalledOnce();
    expect(screen.getAllByRole("button", { name: "Download PDF" })).not.toHaveLength(0);
  });

  it("collapses page and metadata panels without disabling the viewer", async () => {
    const user = userEvent.setup();
    render(<ProjectDrawingViewerPage {...pageProps()} />);
    await user.click(screen.getByRole("button", { name: "Pages" }));
    await user.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.queryByLabelText("PDF page list")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Drawing Details" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Drawing PDF viewport")).toBeInTheDocument();
  });
});
