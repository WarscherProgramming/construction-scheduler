import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useDocumentExplorer from "./useDocumentExplorer";


const apiMocks = vi.hoisted(() => ({
  createFolder: vi.fn(),
  deleteDocument: vi.fn(),
  downloadDocument: vi.fn(),
  exploreDocuments: vi.fn(),
  listFolderTree: vi.fn(),
  listRecentDocuments: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const DOCUMENT = {
  id: 11,
  folder_id: null,
  display_name: "Issued Plans",
  original_filename: "issued-plans.pdf",
  extension: ".pdf",
  mime_type: "application/pdf",
  size_bytes: 1200,
  document_type: "Drawing",
  status: "Active",
  version: 1,
  created_at: "2026-07-30T12:00:00Z",
  updated_at: "2026-07-30T12:00:00Z",
};

const EXPLORER = {
  project_id: 1,
  current_folder: null,
  breadcrumbs: [],
  folders: [],
  documents: [DOCUMENT],
  pagination: {
    limit: 50,
    offset: 0,
    total: 1,
    has_more: false,
  },
};


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}


describe("useDocumentExplorer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.exploreDocuments.mockResolvedValue(EXPLORER);
    apiMocks.listFolderTree.mockResolvedValue({ folders: [] });
    apiMocks.listRecentDocuments.mockResolvedValue({
      documents: [DOCUMENT],
    });
    apiMocks.createFolder.mockResolvedValue({ id: 2, name: "Drawings" });
    apiMocks.uploadDocument.mockResolvedValue(DOCUMENT);
    apiMocks.deleteDocument.mockResolvedValue({
      message: "Document deleted",
    });
    apiMocks.downloadDocument.mockResolvedValue({
      blob: new Blob(["content"], { type: "application/pdf" }),
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="issued-plans.pdf"',
      }),
    });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:document"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("deduplicates initial explorer resources under Strict Mode", async () => {
    const pending = deferred();
    apiMocks.exploreDocuments.mockReturnValue(pending.promise);

    const { result } = renderHook(
      () => useDocumentExplorer({ projectId: 1 }),
      { wrapper: StrictMode }
    );

    expect(result.current.isLoading).toBe(true);
    await waitFor(() =>
      expect(apiMocks.exploreDocuments).toHaveBeenCalledTimes(1)
    );
    await waitFor(() =>
      expect(apiMocks.listFolderTree).toHaveBeenCalledTimes(1)
    );
    expect(apiMocks.listRecentDocuments).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending.resolve(EXPLORER);
      await pending.promise;
    });
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));
  });

  it("applies folder, search, filters, sorting, and pagination", async () => {
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1 })
    );
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));

    act(() => {
      result.current.updateQuery({
        folderId: 8,
        search: "issued",
        documentType: "Drawing",
        extension: ".pdf",
        sort: "updated_at",
        order: "desc",
        offset: 50,
      });
    });

    await waitFor(() =>
      expect(apiMocks.exploreDocuments).toHaveBeenCalledTimes(2)
    );
    expect(apiMocks.exploreDocuments.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        folderId: 8,
        search: "issued",
        documentType: "Drawing",
        extension: ".pdf",
        sort: "updated_at",
        order: "desc",
        offset: 50,
      })
    );
    expect(apiMocks.listFolderTree).toHaveBeenCalledTimes(1);
  });

  it("clears old data and ignores a stale project response", async () => {
    const first = deferred();
    const secondExplorer = {
      ...EXPLORER,
      project_id: 2,
      documents: [{ ...DOCUMENT, id: 22, display_name: "Project Two" }],
    };
    apiMocks.exploreDocuments
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(secondExplorer);
    const hook = renderHook(
      ({ projectId }) => useDocumentExplorer({ projectId }),
      { initialProps: { projectId: 1 } }
    );

    await waitFor(() =>
      expect(apiMocks.exploreDocuments).toHaveBeenCalledTimes(1)
    );
    const firstSignal = apiMocks.exploreDocuments.mock.calls[0][1].signal;
    hook.rerender({ projectId: 2 });

    expect(hook.result.current.explorer).toBeNull();
    await waitFor(() =>
      expect(apiMocks.exploreDocuments).toHaveBeenCalledTimes(2)
    );
    expect(firstSignal.aborted).toBe(true);
    await waitFor(() =>
      expect(hook.result.current.explorer?.project_id).toBe(2)
    );

    await act(async () => {
      first.resolve(EXPLORER);
      await first.promise;
    });
    expect(hook.result.current.explorer.project_id).toBe(2);
  });

  it("uploads files independently, reports partial failure, and retries", async () => {
    const onError = vi.fn();
    apiMocks.uploadDocument
      .mockResolvedValueOnce(DOCUMENT)
      .mockRejectedValueOnce(new Error("Upload unavailable"))
      .mockResolvedValueOnce(DOCUMENT);
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1, onError })
    );
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));
    const files = [
      new File(["%PDF-1.7"], "one.pdf", {
        type: "application/pdf",
      }),
      new File(["%PDF-1.7"], "two.pdf", {
        type: "application/pdf",
      }),
    ];

    await act(async () => {
      await result.current.uploadFiles(files);
    });

    expect(result.current.uploadResults.map((item) => item.status)).toEqual([
      "success",
      "error",
    ]);
    expect(result.current.failedUploadCount).toBe(1);
    expect(onError).toHaveBeenCalledWith(
      "Unable to upload two.pdf",
      expect.any(Error)
    );

    await act(async () => {
      await result.current.retryFailedUploads();
    });
    expect(apiMocks.uploadDocument).toHaveBeenCalledTimes(3);
    expect(apiMocks.uploadDocument.mock.calls[2][1].name).toBe("two.pdf");
    expect(result.current.failedUploadCount).toBe(0);
  });

  it("rejects invalid files locally without blocking valid uploads", async () => {
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1 })
    );
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));
    const invalid = new File(["payload"], "unsafe.exe", {
      type: "application/octet-stream",
    });
    const valid = new File(["%PDF-1.7"], "safe.pdf", {
      type: "application/pdf",
    });

    await act(async () => {
      await result.current.uploadFiles([invalid, valid]);
    });

    expect(apiMocks.uploadDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.uploadDocument.mock.calls[0][1]).toBe(valid);
    expect(result.current.uploadResults[0].message).toMatch(
      /unsupported file type/i
    );
    expect(result.current.uploadResults[1].status).toBe("success");
  });

  it("creates folders in the current location and exposes duplicate failure", async () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1, onError })
    );
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));
    act(() => result.current.updateQuery({ folderId: 9 }));
    await waitFor(() =>
      expect(apiMocks.exploreDocuments).toHaveBeenCalledTimes(2)
    );

    await act(async () => {
      await expect(result.current.createCurrentFolder(" Plans ")).resolves.toBe(
        true
      );
    });
    expect(apiMocks.createFolder).toHaveBeenCalledWith(
      1,
      {
        name: "Plans",
        parent_folder_id: 9,
      },
      { signal: expect.any(AbortSignal) }
    );

    const duplicate = Object.assign(new Error("Already exists"), {
      status: 409,
    });
    apiMocks.createFolder.mockRejectedValueOnce(duplicate);
    await act(async () => {
      await expect(
        result.current.createCurrentFolder("Plans")
      ).resolves.toBe(false);
    });
    expect(result.current.operationError).toBe(duplicate);
    expect(onError).toHaveBeenCalledWith("Unable to create folder", duplicate);
  });

  it("downloads with the safe server filename and soft deletes visibly", async () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1 })
    );
    await waitFor(() => expect(result.current.explorer).toEqual(EXPLORER));

    await act(async () => {
      await expect(result.current.download(DOCUMENT)).resolves.toBe(true);
    });
    expect(click).toHaveBeenCalledOnce();
    expect(URL.createObjectURL).toHaveBeenCalled();

    apiMocks.exploreDocuments.mockResolvedValue({
      ...EXPLORER,
      documents: [],
      pagination: {
        ...EXPLORER.pagination,
        total: 0,
      },
    });
    await act(async () => {
      await expect(result.current.removeDocument(DOCUMENT)).resolves.toBe(
        true
      );
    });
    expect(apiMocks.deleteDocument).toHaveBeenCalledWith(
      DOCUMENT.id,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    await waitFor(() =>
      expect(result.current.explorer?.documents).toEqual([])
    );
    click.mockRestore();
  });

  it("reports access, rate, and network failures without retaining data", async () => {
    const onError = vi.fn();
    const forbidden = Object.assign(new Error("Forbidden"), { status: 403 });
    apiMocks.exploreDocuments.mockRejectedValueOnce(forbidden);
    const { result } = renderHook(() =>
      useDocumentExplorer({ projectId: 1, onError })
    );

    await waitFor(() => expect(result.current.error).toBe(forbidden));
    expect(result.current.explorer).toBeNull();
    expect(onError).toHaveBeenCalledWith(
      "Unable to load project documents",
      forbidden
    );
  });
});
