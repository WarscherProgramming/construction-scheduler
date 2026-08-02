export const DOCUMENT_SEARCH_LIMIT = 20;
export const INITIAL_DOCUMENT_SEARCH_FILTERS = Object.freeze({
  scope: "all",
  documentType: "",
  drawingSetId: "",
  discipline: "",
  currentRevisionsOnly: true,
  extractionMethod: "",
});

const EXTRACTION_STATUS_LABELS = {
  pending: "Processing queued",
  processing: "Processing",
  completed: "Searchable",
  completed_with_warnings: "Searchable with warnings",
  failed: "Extraction failed",
  unavailable: "Search unavailable",
  cancelled: "Extraction cancelled",
};

const EXTRACTION_METHOD_LABELS = {
  embedded_text: "Embedded PDF text",
  ocr: "OCR text",
  mixed: "Embedded and OCR text",
  metadata_only: "Metadata only",
  unavailable: "Content unavailable",
};

export function extractionStatusLabel(extraction) {
  if (!extraction) return "Not processed";
  if (extraction.failure_code === "unsupported_type") return "Not supported";
  if (extraction.failure_code === "ocr_unavailable" && !extraction.searchable) {
    return "OCR unavailable";
  }
  return EXTRACTION_STATUS_LABELS[extraction.status] || "Not processed";
}

export function extractionMethodLabel(method) {
  return EXTRACTION_METHOD_LABELS[method] || "Metadata only";
}

export function normalizeMatchRanges(snippet, ranges) {
  const length = Array.from(String(snippet || "")).length;
  const normalized = (Array.isArray(ranges) ? ranges : [])
    .filter(
      (range) =>
        Number.isInteger(range?.start) &&
        Number.isInteger(range?.end) &&
        range.start >= 0 &&
        range.end > range.start &&
        range.start < length
    )
    .map((range) => ({
      start: range.start,
      end: Math.min(length, range.end),
    }))
    .sort((first, second) => first.start - second.start);

  return normalized.reduce((output, range) => {
    const previous = output.at(-1);
    if (previous && range.start <= previous.end) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      output.push({ ...range });
    }
    return output;
  }, []);
}

export function snippetSegments(snippet, ranges) {
  const text = String(snippet || "");
  const characters = Array.from(text);
  const normalized = normalizeMatchRanges(text, ranges);
  const segments = [];
  let cursor = 0;
  normalized.forEach((range) => {
    if (range.start > cursor) {
      segments.push({
        text: characters.slice(cursor, range.start).join(""),
        match: false,
      });
    }
    segments.push({
      text: characters.slice(range.start, range.end).join(""),
      match: true,
    });
    cursor = range.end;
  });
  if (cursor < characters.length || segments.length === 0) {
    segments.push({
      text: characters.slice(cursor).join(""),
      match: false,
    });
  }
  return segments;
}

export function searchResultNavigation(result, projectId) {
  const target = result?.route_target;
  if (
    target?.type === "drawing_revision" &&
    target.drawing_sheet_id &&
    target.drawing_revision_id
  ) {
    return {
      page: "drawingViewer",
      projectId,
      options: {
        sheetId: target.drawing_sheet_id,
        revisionId: target.drawing_revision_id,
      },
    };
  }
  return { page: "projectDocuments", projectId, options: undefined };
}
