import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useDrawings from "./useDrawings";


const apiMocks = vi.hoisted(() => ({
  addDrawingIssueRevision: vi.fn(),
  archiveDrawingSet: vi.fn(),
  archiveDrawingSheet: vi.fn(),
  createDrawingIssue: vi.fn(),
  createDrawingSet: vi.fn(),
  createDrawingSheet: vi.fn(),
  deleteDrawingIssue: vi.fn(),
  downloadDrawingRevision: vi.fn(),
  getDrawingRegister: vi.fn(),
  issueDrawingIssue: vi.fn(),
  listDrawingIssues: vi.fn(),
  listDrawingRevisions: vi.fn(),
  listDrawingSets: vi.fn(),
  listDrawingSetSheets: vi.fn(),
  removeDrawingIssueRevision: vi.fn(),
  updateDrawingIssue: vi.fn(),
  updateDrawingSet: vi.fn(),
  updateDrawingSheet: vi.fn(),
  uploadDrawingRevision: vi.fn(),
  voidDrawingIssue: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const REVISION = {
  id: 30,
  drawing_sheet_id: 20,
  document_id: 40,
  revision_code: "1",
  revision_date: "2026-07-30",
  sequence_number: 1,
  is_current: true,
  original_filename: "A-101.pdf",
  issue_ids: [],
};

const SHEET = {
  id: 20,
  drawing_set_id: 10,
  sheet_number: "A-101",
  title: "Floor Plan",
  discipline: "A",
  status: "active",
  current_revision: REVISION,
  revision_count: 1,
};

const DRAWING_SET = {
  id: 10,
  project_id: 1,
  name: "IFC",
  status: "active",
  sheet_count: 1,
  issue_count: 0,
};

const REGISTER = {
  project_id: 1,
  sheets: [SHEET],
  pagination: { limit: 50, offset: 0, total: 1, has_more: false },
};


function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}


describe("useDrawings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listDrawingSets.mockResolvedValue({
      drawing_sets: [DRAWING_SET],
    });
    apiMocks.getDrawingRegister.mockResolvedValue(REGISTER);
    apiMocks.listDrawingSetSheets.mockResolvedValue({ sheets: [SHEET] });
    apiMocks.listDrawingIssues.mockResolvedValue({ issues: [] });
    apiMocks.listDrawingRevisions.mockResolvedValue({
      revisions: [REVISION],
    });
    apiMocks.createDrawingSet.mockResolvedValue(DRAWING_SET);
    apiMocks.createDrawingSheet.mockResolvedValue(SHEET);
    apiMocks.uploadDrawingRevision.mockResolvedValue(REVISION);
    apiMocks.addDrawingIssueRevision.mockResolvedValue({ id: 50 });
    apiMocks.issueDrawingIssue.mockResolvedValue({ id: 50, status: "issued" });
    apiMocks.voidDrawingIssue.mockResolvedValue({ id: 50, status: "void" });
    apiMocks.downloadDrawingRevision.mockResolvedValue({
      blob: new Blob(["drawing"], { type: "application/pdf" }),
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="A-101.pdf"',
      }),
    });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:drawing"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("deduplicates project resources under Strict Mode", async () => {
    const { result } = renderHook(
      () => useDrawings({ projectId: 1 }),
      { wrapper: StrictMode }
    );

    await waitFor(() => expect(result.current.register).toEqual(REGISTER));
    await waitFor(() => expect(result.current.drawingSets).toHaveLength(1));
    await waitFor(() => expect(result.current.setSheets).toHaveLength(1));
    expect(apiMocks.listDrawingSets).toHaveBeenCalledOnce();
    expect(apiMocks.getDrawingRegister).toHaveBeenCalledOnce();
    expect(apiMocks.listDrawingSetSheets).toHaveBeenCalledOnce();
    expect(apiMocks.listDrawingIssues).toHaveBeenCalledOnce();
  });

  it("applies register search, filters, sorting, and pagination", async () => {
    const { result } = renderHook(() => useDrawings({ projectId: 1 }));
    await waitFor(() => expect(result.current.register).toEqual(REGISTER));

    act(() =>
      result.current.updateQuery({
        drawingSetId: 10,
        discipline: "A",
        search: "floor",
        sheetStatus: "active",
        sort: "revision_date",
        order: "desc",
        offset: 50,
      })
    );
    await waitFor(() =>
      expect(apiMocks.getDrawingRegister).toHaveBeenCalledTimes(2)
    );
    expect(apiMocks.getDrawingRegister.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        drawingSetId: 10,
        discipline: "A",
        search: "floor",
        sheetStatus: "active",
        sort: "revision_date",
        order: "desc",
        offset: 50,
      })
    );
  });

  it("clears project data and rejects a stale response", async () => {
    const first = deferred();
    apiMocks.getDrawingRegister
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ ...REGISTER, project_id: 2, sheets: [] });
    const hook = renderHook(
      ({ projectId }) => useDrawings({ projectId }),
      { initialProps: { projectId: 1 } }
    );
    await waitFor(() =>
      expect(apiMocks.getDrawingRegister).toHaveBeenCalledOnce()
    );
    hook.rerender({ projectId: 2 });
    expect(hook.result.current.register).toBeNull();
    await waitFor(() =>
      expect(hook.result.current.register?.project_id).toBe(2)
    );
    await act(async () => first.resolve(REGISTER));
    expect(hook.result.current.register?.project_id).toBe(2);
  });

  it("runs sheet and revision uploads once and refreshes resources", async () => {
    const pending = deferred();
    apiMocks.createDrawingSheet.mockReturnValueOnce(pending.promise);
    const { result } = renderHook(() => useDrawings({ projectId: 1 }));
    await waitFor(() => expect(result.current.register).toEqual(REGISTER));
    const file = new File(["%PDF"], "A-101.pdf", {
      type: "application/pdf",
    });

    let first;
    let duplicate;
    act(() => {
      first = result.current.createSheet(10, { sheet_number: "A-101" }, file);
      duplicate = result.current.createSheet(
        10,
        { sheet_number: "A-101" },
        file
      );
    });
    await expect(duplicate).resolves.toBeNull();
    expect(apiMocks.createDrawingSheet).toHaveBeenCalledOnce();
    expect(result.current.activeOperations).toContain("create-sheet");
    await act(async () => pending.resolve(SHEET));
    await expect(first).resolves.toEqual(SHEET);
    await waitFor(() =>
      expect(apiMocks.getDrawingRegister).toHaveBeenCalledTimes(2)
    );

    await act(async () => {
      await result.current.uploadRevision(
        20,
        { revision_code: "2" },
        file
      );
    });
    expect(apiMocks.uploadDrawingRevision).toHaveBeenCalledOnce();
  });

  it("loads history and downloads with the authorized filename", async () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const { result } = renderHook(() => useDrawings({ projectId: 1 }));

    await act(async () => {
      await result.current.loadRevisions(20);
    });
    expect(result.current.revisions).toEqual([REVISION]);
    await act(async () => {
      await result.current.downloadRevision(REVISION);
    });
    expect(apiMocks.downloadDrawingRevision).toHaveBeenCalledWith(
      30,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(click).toHaveBeenCalledOnce();
  });

  it("reports duplicate-set and issue failures without stale state", async () => {
    const error = Object.assign(new Error("Conflict"), { status: 409 });
    const onError = vi.fn();
    apiMocks.createDrawingSet.mockRejectedValueOnce(error);
    apiMocks.addDrawingIssueRevision.mockRejectedValueOnce(error);
    const { result } = renderHook(() =>
      useDrawings({ projectId: 1, onError })
    );
    await waitFor(() => expect(result.current.register).toEqual(REGISTER));

    await act(async () => {
      await expect(
        result.current.createSet({ name: "IFC" })
      ).resolves.toBeNull();
    });
    expect(onError).toHaveBeenCalledWith(
      "Unable to create drawing set",
      error
    );

    await act(async () => {
      await expect(
        result.current.addIssueRevision(50, 30)
      ).resolves.toBeNull();
    });
    expect(result.current.operationError).toBe(error);
    expect(onError).toHaveBeenCalledWith(
      "Unable to add drawing revision to issue",
      error
    );
  });
});
