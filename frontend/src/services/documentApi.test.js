import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createFolder,
  deleteDocument,
  downloadDocument,
  exploreDocuments,
  getDocument,
  listFolderTree,
  listDocuments,
  listFolders,
  listRecentDocuments,
  uploadDocument,
} from "./api";
import { configureAuthentication } from "./httpClient";


function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


describe("document API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("lists project documents and folders with bounded query options", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(jsonResponse({ documents: [], folders: [] }))
      );
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await listDocuments(4, { folderId: 8, limit: 25, offset: 50 });
    await listFolders(4, { limit: 10, offset: 20 });

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/projects/4/documents?folder_id=8&limit=25&offset=50"
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/projects/4/folders?limit=10&offset=20"
    );
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer token-123"
    );
  });

  it("uploads document metadata without forcing a multipart boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }, 201));
    const file = new File(["%PDF-1.7"], "plans.pdf", {
      type: "application/pdf",
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await uploadDocument(3, file, {
      folderId: 7,
      displayName: "Issued Plans",
      documentType: "Drawing",
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/documents/upload");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBeUndefined();
    expect(options.body.get("project_id")).toBe("3");
    expect(options.body.get("folder_id")).toBe("7");
    expect(options.body.get("display_name")).toBe("Issued Plans");
    expect(options.body.get("document_type")).toBe("Drawing");
    expect(options.body.get("file")).toBe(file);
  });

  it("gets, downloads, and soft deletes an authenticated document", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 12 }))
      .mockResolvedValueOnce(
        new Response("binary", {
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'inline; filename="plans.pdf"',
          },
        })
      )
      .mockResolvedValueOnce(jsonResponse({ message: "Document deleted" }));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await expect(getDocument(12)).resolves.toEqual({ id: 12 });
    const download = await downloadDocument(12);
    expect(await download.blob.text()).toBe("binary");
    await expect(deleteDocument(12)).resolves.toEqual({
      message: "Document deleted",
    });

    expect(fetchMock.mock.calls[2][1].method).toBe("DELETE");
  });

  it("creates a folder with an optional parent", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ id: 9, name: "Drawings" }, 201)
    );
    vi.stubGlobal("fetch", fetchMock);

    await createFolder(2, {
      name: "Drawings",
      parent_folder_id: 5,
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/projects/2/folders");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      name: "Drawings",
      parent_folder_id: 5,
    });
  });

  it("requests the explorer, recent documents, and bounded folder tree", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(jsonResponse({})));
    vi.stubGlobal("fetch", fetchMock);

    await exploreDocuments(7, {
      folderId: 2,
      search: "issued plans",
      documentType: "Drawing",
      mimeType: "application/pdf",
      extension: ".pdf",
      sort: "updated_at",
      order: "desc",
      limit: 25,
      offset: 50,
    });
    await listRecentDocuments(7, { limit: 6 });
    await listFolderTree(7);

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/projects/7/documents/explorer?folder_id=2&search=issued+plans&document_type=Drawing&mime_type=application%2Fpdf&extension=.pdf&sort=updated_at&order=desc&limit=25&offset=50"
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/projects/7/documents/recent?limit=6"
    );
    expect(fetchMock.mock.calls[2][0]).toContain(
      "/projects/7/folders/tree"
    );
  });
});
