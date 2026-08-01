import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addDrawingIssueRevision,
  archiveDrawingSet,
  createDrawingIssue,
  createDrawingSet,
  createDrawingSheet,
  downloadDrawingRevision,
  getDrawingSheet,
  getDrawingRegister,
  issueDrawingIssue,
  listDrawingIssues,
  listDrawingRevisions,
  listDrawingSets,
  listDrawingSetSheets,
  removeDrawingIssueRevision,
  updateDrawingIssue,
  updateDrawingSet,
  uploadDrawingRevision,
  voidDrawingIssue,
} from "./api";
import { configureAuthentication } from "./httpClient";


function jsonResponse(body = {}, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


describe("drawing API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("builds bounded register, set, and revision requests", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(jsonResponse())
    );
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "drawing-token" });

    await listDrawingSets(4);
    await getDrawingRegister(4, {
      drawingSetId: 8,
      discipline: "A",
      search: "floor plan",
      sheetStatus: "active",
      sort: "revision_date",
      order: "desc",
      limit: 25,
      offset: 50,
    });
    await listDrawingSetSheets(8);
    await getDrawingSheet(12);
    await listDrawingRevisions(12, { limit: 20, offset: 5 });
    await listDrawingIssues(8);

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/projects/4/drawing-sets"
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "drawing_set_id=8&discipline=A&search=floor+plan"
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "sort=revision_date&order=desc&limit=25&offset=50"
    );
    expect(fetchMock.mock.calls[2][0]).toContain("/drawing-sets/8/sheets");
    expect(fetchMock.mock.calls[3][0]).toContain("/drawing-sheets/12");
    expect(fetchMock.mock.calls[4][0]).toContain(
      "/drawing-sheets/12/revisions?limit=20&offset=5"
    );
    expect(fetchMock.mock.calls[5][0]).toContain("/drawing-sets/8/issues");
  });

  it("uses JSON mutations and multipart PDF uploads safely", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(jsonResponse({ id: 1 }, 201))
    );
    const file = new File(["%PDF-1.7"], "A-101.pdf", {
      type: "application/pdf",
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "drawing-token" });

    await createDrawingSet(4, { name: "IFC" });
    await updateDrawingSet(8, { name: "Issued for Construction" });
    await archiveDrawingSet(8);
    await createDrawingSheet(
      8,
      {
        sheet_number: "A-101",
        title: "Floor Plan",
        discipline: "A",
        revision_code: "0",
        revision_date: "2026-07-30",
      },
      file
    );
    await uploadDrawingRevision(
      12,
      { revision_code: "1", revision_date: "2026-08-01" },
      file
    );

    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[1][1].method).toBe("PATCH");
    expect(fetchMock.mock.calls[2][1].method).toBe("DELETE");
    expect(fetchMock.mock.calls[3][1].body.get("file")).toBe(file);
    expect(
      JSON.parse(fetchMock.mock.calls[3][1].body.get("metadata"))
    ).toMatchObject({ sheet_number: "A-101", revision_code: "0" });
    expect(fetchMock.mock.calls[3][1].headers["Content-Type"]).toBeUndefined();
    expect(fetchMock.mock.calls[4][1].body.get("file")).toBe(file);
  });

  it("uses explicit issue transitions, membership, and download routes", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(jsonResponse())
    );
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "drawing-token" });

    await createDrawingIssue(8, {
      name: "Permit",
      issue_number: "1",
      issue_date: "2026-07-30",
      purpose: "permit",
    });
    await updateDrawingIssue(9, { name: "Permit Submission" });
    await addDrawingIssueRevision(9, 20);
    await removeDrawingIssueRevision(9, 20);
    await issueDrawingIssue(9);
    await voidDrawingIssue(9);
    await downloadDrawingRevision(20);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("/drawing-issues/9/revisions"),
        expect.stringContaining("/drawing-issues/9/revisions/20"),
        expect.stringContaining("/drawing-issues/9/issue"),
        expect.stringContaining("/drawing-issues/9/void"),
        expect.stringContaining("/drawing-revisions/20/download"),
      ])
    );
  });
});
