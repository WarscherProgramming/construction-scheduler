import { describe, expect, it } from "vitest";

import {
  ATTACHMENT_MAX_FILE_SIZE,
  formatAttachmentDateTime,
  formatAttachmentFileSize,
  getAttachmentFileType,
  getSafeAttachmentFilename,
  isAttachmentPreviewEligible,
  isSupportedAttachment,
  parseDownloadFilename,
  validateAttachmentFile,
} from "./attachment";


describe("attachment utilities", () => {
  it("recognizes the supported extension contract case-insensitively", () => {
    for (const filename of [
      "plans.PDF",
      "photo.jpeg",
      "field.heic",
      "report.docx",
      "costs.xlsx",
      "notes.csv",
    ]) {
      expect(isSupportedAttachment(filename)).toBe(true);
    }
    expect(isSupportedAttachment("drawing.svg")).toBe(false);
    expect(isSupportedAttachment("page.html")).toBe(false);
  });

  it("rejects empty, oversized, and unsupported files before upload", () => {
    expect(validateAttachmentFile(new File([], "empty.pdf"))).toContain(
      "empty"
    );
    expect(
      validateAttachmentFile({
        name: "large.pdf",
        size: ATTACHMENT_MAX_FILE_SIZE + 1,
      })
    ).toContain("25 MiB");
    expect(
      validateAttachmentFile({ name: "drawing.svg", size: 20 })
    ).toContain("unsupported");
    expect(
      validateAttachmentFile({
        name: "plans.pdf",
        size: ATTACHMENT_MAX_FILE_SIZE,
      })
    ).toBeNull();
  });

  it("formats file-size boundaries", () => {
    expect(formatAttachmentFileSize(0)).toBe("0 B");
    expect(formatAttachmentFileSize(512)).toBe("512 B");
    expect(formatAttachmentFileSize(1024)).toBe("1.0 KB");
    expect(formatAttachmentFileSize(1.5 * 1024 * 1024)).toBe("1.5 MB");
    expect(formatAttachmentFileSize(25 * 1024 * 1024)).toBe("25.0 MB");
  });

  it("provides readable file-type labels and a safe fallback", () => {
    expect(getAttachmentFileType("plans.pdf")).toBe("PDF");
    expect(getAttachmentFileType("photo.jpg")).toBe("JPEG image");
    expect(getAttachmentFileType("photo.png")).toBe("PNG image");
    expect(getAttachmentFileType("photo.webp")).toBe("WebP image");
    expect(getAttachmentFileType("photo.heic")).toBe("HEIC image");
    expect(getAttachmentFileType("notes.txt")).toBe("Text");
    expect(getAttachmentFileType("data.csv")).toBe("CSV");
    expect(getAttachmentFileType("report.docx")).toBe("Word document");
    expect(getAttachmentFileType("costs.xlsx")).toBe("Excel workbook");
    expect(getAttachmentFileType("unknown.bin")).toBe("File");
  });

  it("previews only PDF and browser-supported raster formats", () => {
    expect(isAttachmentPreviewEligible("plans.pdf")).toBe(true);
    expect(isAttachmentPreviewEligible("photo.jpeg")).toBe(true);
    expect(isAttachmentPreviewEligible("photo.png")).toBe(true);
    expect(isAttachmentPreviewEligible("photo.webp")).toBe(true);
    expect(isAttachmentPreviewEligible("photo.heic")).toBe(false);
    expect(isAttachmentPreviewEligible("report.docx")).toBe(false);
    expect(isAttachmentPreviewEligible("page.svg", "image/svg+xml")).toBe(
      false
    );
  });

  it("uses a safe basename and fallback for filename display", () => {
    expect(getSafeAttachmentFilename("../unsafe/plans.pdf")).toBe(
      "plans.pdf"
    );
    expect(getSafeAttachmentFilename("bad\u0000name.txt")).toBe(
      "badname.txt"
    );
    expect(getSafeAttachmentFilename("")).toBe("Attachment");
    expect(getSafeAttachmentFilename("..")).toBe("Attachment");
  });

  it("parses encoded and quoted download filenames safely", () => {
    expect(
      parseDownloadFilename(
        "attachment; filename*=UTF-8''RFI%20response.pdf",
        "fallback.pdf"
      )
    ).toBe("RFI response.pdf");
    expect(
      parseDownloadFilename(
        'attachment; filename="field report.docx"',
        "fallback.docx"
      )
    ).toBe("field report.docx");
    expect(
      parseDownloadFilename(
        'attachment; filename="../private/plans.pdf"',
        "fallback.pdf"
      )
    ).toBe("plans.pdf");
  });

  it("falls back for missing or malformed headers and invalid dates", () => {
    expect(parseDownloadFilename("", "fallback.pdf")).toBe("fallback.pdf");
    expect(
      parseDownloadFilename(
        "attachment; filename*=UTF-8''%E0%A4%A",
        "fallback.pdf"
      )
    ).toBe("fallback.pdf");
    expect(formatAttachmentDateTime("not-a-date")).toBe("Date unavailable");
    expect(formatAttachmentDateTime(null)).toBe("Date unavailable");
    expect(formatAttachmentDateTime("2026-07-26T12:00:00Z")).not.toContain(
      "Invalid"
    );
  });
});
