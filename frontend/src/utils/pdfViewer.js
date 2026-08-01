import {
  AnnotationMode,
  GlobalWorkerOptions,
  InvalidPDFException,
  PasswordException,
  TextLayer,
  getDocument,
} from "pdfjs-dist";


export const PDF_ZOOM_MIN = 25;
export const PDF_ZOOM_MAX = 400;
export const PDF_ZOOM_STEP = 25;
export const PDF_SEARCH_QUERY_MAX = 200;
export const PDF_THUMBNAIL_RADIUS = 2;
export const PDF_ANNOTATION_MODE_DISABLED = AnnotationMode.DISABLE;

GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();


export function loadPdfDocument(data) {
  return getDocument({
    data: data instanceof Uint8Array ? data : new Uint8Array(data),
    enableXfa: false,
    isEvalSupported: false,
  });
}


export function createPdfTextLayer(options) {
  return new TextLayer(options);
}


export function clampPdfPage(value, pageCount) {
  const page = Number.parseInt(value, 10);
  if (!Number.isFinite(page) || pageCount < 1) return 1;
  return Math.min(pageCount, Math.max(1, page));
}


export function clampPdfZoom(value) {
  return Math.min(PDF_ZOOM_MAX, Math.max(PDF_ZOOM_MIN, value));
}


export function countTextMatches(text, query) {
  if (!query) return 0;
  const source = String(text || "").toLocaleLowerCase();
  const needle = query.toLocaleLowerCase();
  let count = 0;
  let index = 0;
  while ((index = source.indexOf(needle, index)) !== -1) {
    count += 1;
    index += Math.max(needle.length, 1);
  }
  return count;
}


export function pdfLoadErrorMessage(error) {
  if (error instanceof PasswordException || error?.name === "PasswordException") {
    return "Password-protected or encrypted PDFs are not supported in the viewer.";
  }
  if (error instanceof InvalidPDFException || error?.name === "InvalidPDFException") {
    return "This PDF is corrupt or is not a supported PDF document.";
  }
  if (error?.status === 403 || error?.status === 404) {
    return "This drawing revision is unavailable or you do not have access to it.";
  }
  if (error?.status === 401) {
    return "Your session could not be refreshed. Sign in and try again.";
  }
  return "The drawing revision could not be loaded. Try again.";
}
