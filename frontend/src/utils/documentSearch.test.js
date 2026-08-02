import { describe, expect, it } from "vitest";

import {
  extractionMethodLabel,
  extractionStatusLabel,
  normalizeMatchRanges,
  searchResultNavigation,
  snippetSegments,
} from "./documentSearch";


describe("document search utilities", () => {
  it("labels factual extraction states and methods", () => {
    expect(extractionStatusLabel({ status: "processing" })).toBe("Processing");
    expect(
      extractionStatusLabel({
        status: "unavailable",
        failure_code: "ocr_unavailable",
        searchable: false,
      })
    ).toBe("OCR unavailable");
    expect(
      extractionStatusLabel({ failure_code: "unsupported_type" })
    ).toBe("Not supported");
    expect(extractionMethodLabel("mixed")).toBe("Embedded and OCR text");
  });

  it("bounds and merges untrusted match ranges", () => {
    expect(
      normalizeMatchRanges("<script> & text", [
        { start: -1, end: 4 },
        { start: 1, end: 4 },
        { start: 3, end: 9 },
        { start: 100, end: 200 },
      ])
    ).toEqual([{ start: 1, end: 9 }]);
    expect(
      snippetSegments("<script>", [{ start: 0, end: 8 }])
    ).toEqual([{ text: "<script>", match: true }]);
    expect(
      snippetSegments("😀 AHU-42", [{ start: 2, end: 8 }])
    ).toEqual([
      { text: "😀 ", match: false },
      { text: "AHU-42", match: true },
    ]);
  });

  it("builds exact drawing navigation and document fallback", () => {
    expect(
      searchResultNavigation(
        {
          route_target: {
            type: "drawing_revision",
            drawing_sheet_id: 7,
            drawing_revision_id: 9,
          },
        },
        4
      )
    ).toEqual({
      page: "drawingViewer",
      projectId: 4,
      options: { sheetId: 7, revisionId: 9 },
    });
    expect(searchResultNavigation({}, 4)).toEqual({
      page: "projectDocuments",
      projectId: 4,
      options: undefined,
    });
  });
});
