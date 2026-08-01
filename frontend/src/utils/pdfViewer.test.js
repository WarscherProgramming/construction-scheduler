import { beforeEach, describe, expect, it, vi } from "vitest";


const pdfMocks = vi.hoisted(() => {
  class InvalidPDFException extends Error {}
  class PasswordException extends Error {}
  return {
    AnnotationMode: { DISABLE: 0 },
    GlobalWorkerOptions: {},
    InvalidPDFException,
    PasswordException,
    TextLayer: vi.fn(),
    getDocument: vi.fn(),
  };
});

vi.mock("pdfjs-dist", () => pdfMocks);

import {
  clampPdfPage,
  clampPdfZoom,
  countTextMatches,
  createPdfTextLayer,
  loadPdfDocument,
  PDF_ANNOTATION_MODE_DISABLED,
  pdfLoadErrorMessage,
} from "./pdfViewer";


describe("PDF viewer utilities", () => {
  beforeEach(() => vi.clearAllMocks());

  it("configures a same-origin emitted worker and security-focused loading", () => {
    const bytes = new Uint8Array([1, 2, 3]);
    loadPdfDocument(bytes);

    expect(pdfMocks.GlobalWorkerOptions.workerSrc).toContain("pdf.worker.min");
    expect(pdfMocks.getDocument).toHaveBeenCalledWith({
      data: bytes,
      enableXfa: false,
      isEvalSupported: false,
    });
    expect(PDF_ANNOTATION_MODE_DISABLED).toBe(0);
  });

  it("creates the official selectable text layer without HTML injection", () => {
    const options = { container: document.createElement("div") };
    createPdfTextLayer(options);
    expect(pdfMocks.TextLayer).toHaveBeenCalledWith(options);
  });

  it("clamps page and zoom input to documented limits", () => {
    expect(clampPdfPage("0", 10)).toBe(1);
    expect(clampPdfPage("99", 10)).toBe(10);
    expect(clampPdfZoom(5)).toBe(25);
    expect(clampPdfZoom(500)).toBe(400);
  });

  it("counts literal case-insensitive text without regex behavior", () => {
    expect(countTextMatches("Door door DOOR", "door")).toBe(3);
    expect(countTextMatches("A.*B A.*B", ".*")).toBe(2);
  });

  it("maps encrypted, corrupt, and access errors to safe messages", () => {
    expect(pdfLoadErrorMessage(new pdfMocks.PasswordException())).toContain(
      "Password-protected"
    );
    expect(pdfLoadErrorMessage(new pdfMocks.InvalidPDFException())).toContain(
      "corrupt"
    );
    expect(pdfLoadErrorMessage({ status: 404 })).toContain("unavailable");
    expect(pdfLoadErrorMessage(new Error("local path C:\\secret"))).not.toContain(
      "secret"
    );
  });
});
