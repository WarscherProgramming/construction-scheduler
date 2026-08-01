import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  downloadDrawingRevision,
  getDrawingSheet,
  listDrawingRevisions,
  listDrawingSetSheets,
} from "../services/api";
import {
  getSafeAttachmentFilename,
  parseDownloadFilename,
} from "../utils/attachment";
import {
  PDF_SEARCH_QUERY_MAX,
  PDF_ZOOM_STEP,
  clampPdfPage,
  clampPdfZoom,
  countTextMatches,
  loadPdfDocument,
  pdfLoadErrorMessage,
} from "../utils/pdfViewer";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function unavailableRevisionError() {
  return Object.assign(new Error("Drawing revision not found"), { status: 404 });
}


function initialSearchState() {
  return {
    query: "",
    matches: [],
    matchIndex: -1,
    isIndexing: false,
    hasText: null,
    error: "",
  };
}


function triggerBlobDownload(blob, filename, urlsRef) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  const timer = window.setTimeout(() => {
    window.URL.revokeObjectURL(url);
    urlsRef.current.delete(url);
  }, 0);
  urlsRef.current.set(url, timer);
}


function useDrawingViewer({ projectId, sheetId, revisionId, onError }) {
  const identity = `${projectId}:${sheetId}:${revisionId}`;
  const [resolvedIdentity, setResolvedIdentity] = useState(null);
  const [sheet, setSheet] = useState(null);
  const [revision, setRevision] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [setSheets, setSetSheets] = useState([]);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [pdfBlob, setPdfBlob] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState("Drawing.pdf");
  const [pageCount, setPageCount] = useState(0);
  const [currentPage, setCurrentPageState] = useState(1);
  const [zoomMode, setZoomMode] = useState("fit-width");
  const [zoomPercent, setZoomPercent] = useState(100);
  const [phase, setPhase] = useState("metadata");
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);
  const [search, setSearch] = useState(initialSearchState);
  const pdfDocumentRef = useRef(null);
  const loadingTaskRef = useRef(null);
  const generationRef = useRef(0);
  const searchGenerationRef = useRef(0);
  const currentPageRef = useRef(1);
  const objectUrlsRef = useRef(new Map());

  const setCurrentPage = useCallback(
    (value) => {
      const nextPage = clampPdfPage(value, pageCount);
      currentPageRef.current = nextPage;
      setCurrentPageState(nextPage);
    },
    [pageCount]
  );

  useEffect(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    searchGenerationRef.current += 1;
    const controller = new AbortController();
    let timeoutId;

    pdfDocumentRef.current?.destroy();
    pdfDocumentRef.current = null;
    loadingTaskRef.current?.destroy();
    loadingTaskRef.current = null;

    const load = async () => {
      setResolvedIdentity(identity);
      setSheet(null);
      setRevision(null);
      setRevisions([]);
      setSetSheets([]);
      setPdfDocument(null);
      setPdfBlob(null);
      setPageCount(0);
      setSearch(initialSearchState());
      setError(null);
      setPhase("metadata");
      try {
        const [sheetResponse, historyResponse] = await Promise.all([
          getDrawingSheet(sheetId, { signal: controller.signal }),
          listDrawingRevisions(sheetId, {
            limit: 100,
            signal: controller.signal,
          }),
        ]);
        const history = historyResponse?.revisions || [];
        const requestedRevision = history.find(
          (item) => item.id === Number(revisionId)
        );
        if (
          sheetResponse.project_id !== Number(projectId) ||
          sheetResponse.id !== Number(sheetId) ||
          !requestedRevision ||
          requestedRevision.drawing_sheet_id !== Number(sheetId)
        ) {
          throw unavailableRevisionError();
        }
        if (generation !== generationRef.current || controller.signal.aborted) return;

        setSheet(sheetResponse);
        setRevision(requestedRevision);
        setRevisions(history);
        setPhase("download");

        const navigationPromise = listDrawingSetSheets(
          sheetResponse.drawing_set_id,
          { signal: controller.signal }
        ).catch((navigationError) => {
          if (!isAbortError(navigationError)) {
            onError?.("Unable to load drawing sheet navigation", navigationError);
          }
          return { sheets: [] };
        });
        const [navigationResponse, downloadResponse] = await Promise.all([
          navigationPromise,
          downloadDrawingRevision(requestedRevision.id, {
            signal: controller.signal,
          }),
        ]);
        if (generation !== generationRef.current || controller.signal.aborted) return;

        setSetSheets(
          (navigationResponse?.sheets || []).filter(
            (item) => item.status === "active" && item.current_revision
          )
        );
        setPdfBlob(downloadResponse.blob);
        setDownloadFilename(
          parseDownloadFilename(
            downloadResponse.headers?.get?.("content-disposition"),
            getSafeAttachmentFilename(
              requestedRevision.original_filename,
              "Drawing.pdf"
            )
          )
        );
        setPhase("parsing");
        const bytes = await downloadResponse.blob.arrayBuffer();
        if (generation !== generationRef.current || controller.signal.aborted) return;

        const loadingTask = loadPdfDocument(bytes);
        loadingTaskRef.current = loadingTask;
        const loadedDocument = await loadingTask.promise;
        if (generation !== generationRef.current || controller.signal.aborted) {
          await loadedDocument.destroy();
          return;
        }
        loadingTaskRef.current = null;
        pdfDocumentRef.current = loadedDocument;
        setPdfDocument(loadedDocument);
        setPageCount(loadedDocument.numPages);
        const nextPage = clampPdfPage(currentPageRef.current, loadedDocument.numPages);
        currentPageRef.current = nextPage;
        setCurrentPageState(nextPage);
        setPhase("ready");
      } catch (loadError) {
        if (
          isAbortError(loadError) ||
          controller.signal.aborted ||
          generation !== generationRef.current
        ) {
          return;
        }
        setError({ cause: loadError, message: pdfLoadErrorMessage(loadError) });
        setPhase("error");
        onError?.("Unable to load drawing revision", loadError);
      }
    };

    timeoutId = window.setTimeout(load, 0);
    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
      searchGenerationRef.current += 1;
      loadingTaskRef.current?.destroy();
      loadingTaskRef.current = null;
      pdfDocumentRef.current?.destroy();
      pdfDocumentRef.current = null;
    };
  }, [identity, onError, projectId, retryKey, revisionId, sheetId]);

  useEffect(
    () => () => {
      objectUrlsRef.current.forEach((timer, url) => {
        window.clearTimeout(timer);
        window.URL.revokeObjectURL(url);
      });
      objectUrlsRef.current.clear();
    },
    []
  );

  const searchPdf = useCallback(
    async (rawQuery) => {
      const query = String(rawQuery || "").trim().slice(0, PDF_SEARCH_QUERY_MAX);
      const searchGeneration = searchGenerationRef.current + 1;
      searchGenerationRef.current = searchGeneration;
      if (!query || !pdfDocument) {
        setSearch(initialSearchState());
        return;
      }
      setSearch({
        query,
        matches: [],
        matchIndex: -1,
        isIndexing: true,
        hasText: null,
        error: "",
      });
      const matches = [];
      let extractedCharacters = 0;
      try {
        for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
          const page = await pdfDocument.getPage(pageNumber);
          const content = await page.getTextContent();
          const text = content.items.map((item) => item.str || "").join(" ");
          extractedCharacters += text.trim().length;
          const count = countTextMatches(text, query);
          for (let index = 0; index < count; index += 1) matches.push(pageNumber);
          if (searchGeneration !== searchGenerationRef.current) return;
        }
        setSearch({
          query,
          matches,
          matchIndex: matches.length ? 0 : -1,
          isIndexing: false,
          hasText: extractedCharacters > 0,
          error: "",
        });
        if (matches.length) setCurrentPage(matches[0]);
      } catch {
        if (searchGeneration !== searchGenerationRef.current) return;
        setSearch({
          query,
          matches: [],
          matchIndex: -1,
          isIndexing: false,
          hasText: null,
          error: "Searchable text could not be read from this revision.",
        });
      }
    },
    [pdfDocument, setCurrentPage]
  );

  const moveSearchMatch = useCallback(
    (direction) => {
      if (!search.matches.length) return;
      const matchIndex =
        (search.matchIndex + direction + search.matches.length) %
        search.matches.length;
      setCurrentPage(search.matches[matchIndex]);
      setSearch({ ...search, matchIndex });
    },
    [search, setCurrentPage]
  );

  const clearSearch = useCallback(() => {
    searchGenerationRef.current += 1;
    setSearch(initialSearchState());
  }, []);

  const changeZoom = useCallback((delta) => {
    setZoomPercent((current) => clampPdfZoom(current + delta));
    setZoomMode("percent");
  }, []);

  const resetZoom = useCallback(() => {
    setZoomPercent(100);
    setZoomMode("percent");
  }, []);

  const download = useCallback(() => {
    if (!pdfBlob) return false;
    triggerBlobDownload(pdfBlob, downloadFilename, objectUrlsRef);
    return true;
  }, [downloadFilename, pdfBlob]);

  const sheetPosition = useMemo(
    () => setSheets.findIndex((item) => item.id === Number(sheetId)),
    [setSheets, sheetId]
  );

  const isCurrentIdentity = resolvedIdentity === identity;

  return {
    sheet: isCurrentIdentity ? sheet : null,
    revision: isCurrentIdentity ? revision : null,
    revisions: isCurrentIdentity ? revisions : [],
    setSheets: isCurrentIdentity ? setSheets : [],
    sheetPosition,
    previousSheet: sheetPosition > 0 ? setSheets[sheetPosition - 1] : null,
    nextSheet:
      sheetPosition >= 0 && sheetPosition < setSheets.length - 1
        ? setSheets[sheetPosition + 1]
        : null,
    pdfDocument: isCurrentIdentity ? pdfDocument : null,
    pageCount: isCurrentIdentity ? pageCount : 0,
    currentPage,
    setCurrentPage,
    zoomMode,
    zoomPercent,
    zoomIn: () => changeZoom(PDF_ZOOM_STEP),
    zoomOut: () => changeZoom(-PDF_ZOOM_STEP),
    resetZoom,
    fitWidth: () => setZoomMode("fit-width"),
    fitPage: () => setZoomMode("fit-page"),
    search,
    searchPdf,
    moveSearchMatch,
    clearSearch,
    phase: isCurrentIdentity ? phase : "metadata",
    error: isCurrentIdentity ? error : null,
    retry: () => setRetryKey((current) => current + 1),
    canDownload: isCurrentIdentity && Boolean(pdfBlob),
    download,
  };
}

export default useDrawingViewer;
