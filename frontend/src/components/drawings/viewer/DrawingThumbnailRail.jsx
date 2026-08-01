import { useEffect, useMemo, useRef, useState } from "react";

import {
  PDF_ANNOTATION_MODE_DISABLED,
  PDF_THUMBNAIL_RADIUS,
} from "../../../utils/pdfViewer";


function PdfThumbnail({ pdfDocument, pageNumber, activePage }) {
  const canvasRef = useRef(null);
  const [failed, setFailed] = useState(false);
  const shouldRender = Math.abs(pageNumber - activePage) <= PDF_THUMBNAIL_RADIUS;

  useEffect(() => {
    if (!shouldRender || !pdfDocument || !canvasRef.current) return undefined;
    let cancelled = false;
    let renderTask;
    const render = async () => {
      try {
        const page = await pdfDocument.getPage(pageNumber);
        if (cancelled) return;
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: 112 / base.width });
        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d", { alpha: false });
        if (!canvas || !context) return;
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        renderTask = page.render({
          canvas,
          canvasContext: context,
          viewport,
          annotationMode: PDF_ANNOTATION_MODE_DISABLED,
        });
        await renderTask.promise;
      } catch (error) {
        if (error?.name !== "RenderingCancelledException" && !cancelled) {
          setFailed(true);
        }
      }
    };
    void render();
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [pageNumber, pdfDocument, shouldRender]);

  if (!shouldRender || failed) return <span className="drawing-thumbnail-placeholder">Page {pageNumber}</span>;
  return <canvas ref={canvasRef} aria-hidden="true" />;
}


function DrawingThumbnailRail({ pdfDocument, pageCount, currentPage, onSelect }) {
  const pages = useMemo(() => {
    const size = Math.min(31, pageCount);
    let start = Math.max(1, currentPage - 15);
    start = Math.min(start, Math.max(1, pageCount - size + 1));
    return Array.from({ length: size }, (_, index) => start + index);
  }, [currentPage, pageCount]);

  if (!pageCount) return null;
  return (
    <aside className="drawing-thumbnail-rail" aria-label="PDF page list">
      <p className="drawing-thumbnail-range">
        Pages {pages[0]}-{pages.at(-1)} of {pageCount}
      </p>
      <ol>
        {pages.map((pageNumber) => (
          <li key={pageNumber}>
            <button
              type="button"
              className={pageNumber === currentPage ? "is-current" : ""}
              aria-current={pageNumber === currentPage ? "page" : undefined}
              aria-label={`View PDF page ${pageNumber}`}
              onClick={() => onSelect(pageNumber)}
            >
              <PdfThumbnail
                pdfDocument={pdfDocument}
                pageNumber={pageNumber}
                activePage={currentPage}
              />
              <span>Page {pageNumber}</span>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
}

export default DrawingThumbnailRail;
