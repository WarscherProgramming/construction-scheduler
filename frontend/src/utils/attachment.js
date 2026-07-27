export const ATTACHMENT_MAX_FILE_SIZE = 26_214_400;

export const ATTACHMENT_PARENT_TYPES = Object.freeze({
  PROJECT: "project",
  DAILY_LOG: "daily_log",
  RFI: "rfi",
  SUBMITTAL: "submittal",
  PUNCH_ITEM: "punch_item",
  CHANGE_ORDER: "change_order",
});

export const SUPPORTED_ATTACHMENT_EXTENSIONS = Object.freeze([
  ".pdf",
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".heic",
  ".heif",
  ".txt",
  ".csv",
  ".doc",
  ".xls",
  ".docx",
  ".xlsx",
]);

export const ATTACHMENT_ACCEPT = [
  ...SUPPORTED_ATTACHMENT_EXTENSIONS,
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "text/plain",
  "text/csv",
  "application/msword",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
].join(",");

const SUPPORTED_EXTENSION_SET = new Set(SUPPORTED_ATTACHMENT_EXTENSIONS);
const PREVIEW_EXTENSIONS = new Set([
  ".pdf",
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
]);
const PREVIEW_MIME_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
]);

const FILE_TYPE_LABELS = {
  ".pdf": "PDF",
  ".jpg": "JPEG image",
  ".jpeg": "JPEG image",
  ".png": "PNG image",
  ".webp": "WebP image",
  ".heic": "HEIC image",
  ".heif": "HEIC image",
  ".txt": "Text",
  ".csv": "CSV",
  ".doc": "Word document",
  ".docx": "Word document",
  ".xls": "Excel workbook",
  ".xlsx": "Excel workbook",
};


export function getAttachmentExtension(filename) {
  const safeName = getSafeAttachmentFilename(filename, "");
  const dotIndex = safeName.lastIndexOf(".");
  if (dotIndex <= 0) return "";
  return safeName.slice(dotIndex).toLowerCase();
}


export function isSupportedAttachment(filename) {
  return SUPPORTED_EXTENSION_SET.has(getAttachmentExtension(filename));
}


export function validateAttachmentFile(file) {
  if (!file || !file.name) {
    return "Select a valid file.";
  }
  if (file.size === 0) {
    return `${getSafeAttachmentFilename(file.name)} is empty.`;
  }
  if (file.size > ATTACHMENT_MAX_FILE_SIZE) {
    return `${getSafeAttachmentFilename(file.name)} exceeds the 25 MiB limit.`;
  }
  if (!isSupportedAttachment(file.name)) {
    return `${getSafeAttachmentFilename(file.name)} has an unsupported file type.`;
  }
  return null;
}


export function formatAttachmentFileSize(sizeBytes) {
  const size = Number(sizeBytes);
  if (!Number.isFinite(size) || size <= 0) return "0 B";
  if (size < 1024) return `${Math.round(size)} B`;

  const units = ["KB", "MB", "GB"];
  let value = size / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}


export function getAttachmentFileType(filename, mimeType = "") {
  const extension = getAttachmentExtension(filename);
  if (FILE_TYPE_LABELS[extension]) {
    return FILE_TYPE_LABELS[extension];
  }

  const normalizedMime = String(mimeType).toLowerCase();
  if (normalizedMime === "application/pdf") return "PDF";
  if (normalizedMime === "image/jpeg") return "JPEG image";
  if (normalizedMime === "image/png") return "PNG image";
  if (normalizedMime === "image/webp") return "WebP image";
  if (normalizedMime === "image/heic" || normalizedMime === "image/heif") {
    return "HEIC image";
  }
  if (normalizedMime === "text/plain") return "Text";
  if (normalizedMime === "text/csv") return "CSV";
  return "File";
}


export function isAttachmentPreviewEligible(filename, mimeType = "") {
  const extension = getAttachmentExtension(filename);
  const normalizedMime = String(mimeType).split(";", 1)[0].toLowerCase();
  return (
    PREVIEW_EXTENSIONS.has(extension) ||
    PREVIEW_MIME_TYPES.has(normalizedMime)
  );
}


export function getSafeAttachmentFilename(
  filename,
  fallback = "Attachment"
) {
  const normalized = Array.from(
    String(filename || "")
    .normalize("NFKC")
    .replaceAll("\\", "/")
    .split("/")
    .pop()
  )
    .filter((character) => {
      const codePoint = character.codePointAt(0);
      return codePoint > 31 && (codePoint < 127 || codePoint > 159);
    })
    .join("")
    .trim();

  return normalized && normalized !== "." && normalized !== ".."
    ? normalized
    : fallback;
}


export function parseDownloadFilename(headerValue, fallback = "Attachment") {
  const header = String(headerValue || "");
  const encodedMatch = header.match(
    /filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i
  );

  if (encodedMatch) {
    try {
      const encoded = encodedMatch[1].trim().replace(/^"|"$/g, "");
      return getSafeAttachmentFilename(
        decodeURIComponent(encoded),
        fallback
      );
    } catch {
      return getSafeAttachmentFilename(fallback);
    }
  }

  const quotedMatch = header.match(/filename\s*=\s*"((?:\\.|[^"])*)"/i);
  const plainMatch = header.match(/filename\s*=\s*([^;]+)/i);
  const candidate = quotedMatch?.[1]?.replace(/\\"/g, '"') || plainMatch?.[1];

  return getSafeAttachmentFilename(
    candidate?.trim().replace(/^"|"$/g, ""),
    fallback
  );
}


export function formatAttachmentDateTime(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
