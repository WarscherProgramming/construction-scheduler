import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useDrawingViewer from "./useDrawingViewer";


const apiMocks = vi.hoisted(() => ({
  downloadDrawingRevision: vi.fn(),
  getDrawingSheet: vi.fn(),
  listDrawingRevisions: vi.fn(),
  listDrawingSetSheets: vi.fn(),
}));
const pdfMocks = vi.hoisted(() => ({ loadPdfDocument: vi.fn() }));

vi.mock("../services/api", () => apiMocks);
vi.mock("../utils/pdfViewer", () => ({
  PDF_SEARCH_QUERY_MAX: 200,
  PDF_ZOOM_STEP: 25,
  clampPdfPage: (value, count) => Math.min(count, Math.max(1, Number.parseInt(value, 10) || 1)),
  clampPdfZoom: (value) => Math.min(400, Math.max(25, value)),
  countTextMatches: (text, query) =>
    String(text).toLowerCase().split(String(query).toLowerCase()).length - 1,
  loadPdfDocument: pdfMocks.loadPdfDocument,
  pdfLoadErrorMessage: (error) => error.message || "Unable to load",
}));


const REVISION = {
  id: 30,
  project_id: 1,
  drawing_sheet_id: 20,
  revision_code: "1",
  revision_date: "2026-08-01",
  sequence_number: 2,
  is_current: true,
  original_filename: "A-101-r1.pdf",
  issue_ids: [],
};
const SHEET = {
  id: 20,
  project_id: 1,
  drawing_set_id: 10,
  drawing_set_name: "IFC",
  sheet_number: "A-101",
  title: "Floor Plan",
  status: "active",
  current_revision: REVISION,
};


function makePdfDocument(textByPage = ["floor plan", "door detail"]) {
  return {
    numPages: textByPage.length,
    destroy: vi.fn().mockResolvedValue(undefined),
    getPage: vi.fn(async (pageNumber) => ({
      getTextContent: vi.fn().mockResolvedValue({
        items: [{ str: textByPage[pageNumber - 1] }],
      }),
    })),
  };
}


function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}


describe("useDrawingViewer", () => {
  let pdfDocument;
  let loadingTask;

  beforeEach(() => {
    vi.clearAllMocks();
    pdfDocument = makePdfDocument();
    loadingTask = {
      promise: Promise.resolve(pdfDocument),
      destroy: vi.fn().mockResolvedValue(undefined),
    };
    pdfMocks.loadPdfDocument.mockReturnValue(loadingTask);
    apiMocks.getDrawingSheet.mockResolvedValue(SHEET);
    apiMocks.listDrawingRevisions.mockResolvedValue({ revisions: [REVISION] });
    apiMocks.listDrawingSetSheets.mockResolvedValue({ sheets: [SHEET] });
    apiMocks.downloadDrawingRevision.mockResolvedValue({
      blob: { arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)) },
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="A-101-r1.pdf"',
      }),
    });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:drawing-viewer"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("loads metadata, navigation, and one PDF request under Strict Mode", async () => {
    const { result } = renderHook(
      () => useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 }),
      { wrapper: StrictMode }
    );

    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.sheet).toEqual(SHEET);
    expect(result.current.pageCount).toBe(2);
    expect(apiMocks.getDrawingSheet).toHaveBeenCalledOnce();
    expect(apiMocks.listDrawingRevisions).toHaveBeenCalledOnce();
    expect(apiMocks.listDrawingSetSheets).toHaveBeenCalledOnce();
    expect(apiMocks.downloadDrawingRevision).toHaveBeenCalledOnce();
  });

  it("rejects a revision paired with the wrong sheet before download", async () => {
    const onError = vi.fn();
    apiMocks.listDrawingRevisions.mockResolvedValue({
      revisions: [{ ...REVISION, drawing_sheet_id: 99 }],
    });
    const { result } = renderHook(() =>
      useDrawingViewer({
        projectId: 1,
        sheetId: 20,
        revisionId: 30,
        onError,
      })
    );

    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(apiMocks.downloadDrawingRevision).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      "Unable to load drawing revision",
      expect.objectContaining({ status: 404 })
    );
  });

  it("searches existing text lazily and moves between matches", async () => {
    pdfDocument = makePdfDocument(["Door door", "No match"]);
    pdfMocks.loadPdfDocument.mockReturnValue({
      promise: Promise.resolve(pdfDocument),
      destroy: vi.fn(),
    });
    const { result } = renderHook(() =>
      useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 })
    );
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(pdfDocument.getPage).not.toHaveBeenCalled();

    await act(() => result.current.searchPdf(" door "));
    expect(result.current.search.matches).toEqual([1, 1]);
    expect(result.current.search.hasText).toBe(true);

    act(() => result.current.moveSearchMatch(1));
    expect(result.current.search.matchIndex).toBe(1);
    act(() => result.current.clearSearch());
    expect(result.current.search.query).toBe("");
  });

  it("reports when an image-only PDF has no searchable text", async () => {
    pdfDocument = makePdfDocument(["", ""]);
    pdfMocks.loadPdfDocument.mockReturnValue({
      promise: Promise.resolve(pdfDocument),
      destroy: vi.fn(),
    });
    const { result } = renderHook(() =>
      useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 })
    );
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    await act(() => result.current.searchPdf("note"));
    expect(result.current.search.hasText).toBe(false);
    expect(result.current.search.matches).toEqual([]);
  });

  it("reuses loaded bytes for download and revokes the temporary URL", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 })
    );
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.phase).toBe("ready");

    act(() => result.current.download());
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(apiMocks.downloadDrawingRevision).toHaveBeenCalledOnce();
    act(() => vi.runAllTimers());
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:drawing-viewer");
    vi.useRealTimers();
  });

  it("destroys the PDF document and aborts requests on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 })
    );
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    const signal = apiMocks.getDrawingSheet.mock.calls[0][1].signal;

    unmount();
    expect(signal.aborted).toBe(true);
    expect(pdfDocument.destroy).toHaveBeenCalled();
  });

  it("clears the prior identity and rejects stale revision responses", async () => {
    const firstSheet = deferred();
    const firstHistory = deferred();
    const nextRevision = {
      ...REVISION,
      id: 31,
      drawing_sheet_id: 21,
      revision_code: "2",
    };
    const nextSheet = {
      ...SHEET,
      id: 21,
      current_revision: nextRevision,
    };
    apiMocks.getDrawingSheet
      .mockReset()
      .mockReturnValueOnce(firstSheet.promise)
      .mockResolvedValue(nextSheet);
    apiMocks.listDrawingRevisions
      .mockReset()
      .mockReturnValueOnce(firstHistory.promise)
      .mockResolvedValue({ revisions: [nextRevision] });

    const { result, rerender } = renderHook(
      ({ activeSheetId, activeRevisionId }) =>
        useDrawingViewer({
          projectId: 1,
          sheetId: activeSheetId,
          revisionId: activeRevisionId,
        }),
      { initialProps: { activeSheetId: 20, activeRevisionId: 30 } }
    );
    await waitFor(() => expect(apiMocks.getDrawingSheet).toHaveBeenCalledOnce());
    rerender({ activeSheetId: 21, activeRevisionId: 31 });
    expect(result.current.sheet).toBeNull();
    expect(result.current.phase).toBe("metadata");
    await waitFor(() => expect(result.current.sheet?.id).toBe(21));

    await act(async () => {
      firstSheet.resolve(SHEET);
      firstHistory.resolve({ revisions: [REVISION] });
    });
    expect(result.current.sheet.id).toBe(21);
    expect(apiMocks.downloadDrawingRevision).toHaveBeenCalledOnce();
  });

  it("retries a failed PDF request without duplicating settled work", async () => {
    apiMocks.downloadDrawingRevision
      .mockRejectedValueOnce(new Error("Network unavailable"))
      .mockResolvedValueOnce({
        blob: { arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)) },
        headers: new Headers(),
      });
    const { result } = renderHook(() =>
      useDrawingViewer({ projectId: 1, sheetId: 20, revisionId: 30 })
    );
    await waitFor(() => expect(result.current.phase).toBe("error"));

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(apiMocks.downloadDrawingRevision).toHaveBeenCalledTimes(2);
  });
});
