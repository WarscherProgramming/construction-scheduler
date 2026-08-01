import { useEffect, useRef, useState } from "react";

import {
  PDF_ANNOTATION_MODE_DISABLED,
  createPdfTextLayer,
} from "../../../utils/pdfViewer";
import Button from "../../ui/Button";


function PdfCanvasViewport({
  pdfDocument,
  pageNumber,
  zoomMode,
  zoomPercent,
  sheetLabel,
  onRenderStateChange,
}) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const textLayerRef = useRef(null);
  const [containerSize, setContainerSize] = useState({ width: 900, height: 700 });
  const [renderError, setRenderError] = useState("");
  const [renderKey, setRenderKey] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    let frame;
    const update = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        setContainerSize({
          width: Math.max(240, container.clientWidth - 32),
          height: Math.max(320, container.clientHeight - 32),
        });
      });
    };
    update();
    if (typeof ResizeObserver === "undefined") return () => window.cancelAnimationFrame(frame);
    const observer = new ResizeObserver(update);
    observer.observe(container);
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!pdfDocument || !canvasRef.current) return undefined;
    let cancelled = false;
    let renderTask;
    let textLayer;
    setRenderError("");
    onRenderStateChange?.("rendering");
    const render = async () => {
      try {
        const page = await pdfDocument.getPage(pageNumber);
        if (cancelled) return;
        const baseViewport = page.getViewport({ scale: 1 });
        let scale = zoomPercent / 100;
        if (zoomMode === "fit-width") scale = containerSize.width / baseViewport.width;
        if (zoomMode === "fit-page") {
          scale = Math.min(
            containerSize.width / baseViewport.width,
            containerSize.height / baseViewport.height
          );
        }
        const viewport = page.getViewport({ scale: Math.max(scale, 0.01) });
        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d", { alpha: false });
        if (!canvas || !context) throw new Error("Canvas rendering is unavailable");
        const outputScale = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        canvas.parentElement?.style.setProperty(
          "--total-scale-factor",
          String(Math.max(scale, 0.01))
        );
        const transform = outputScale === 1 ? null : [outputScale, 0, 0, outputScale, 0, 0];
        renderTask = page.render({
          canvas,
          canvasContext: context,
          viewport,
          transform,
          annotationMode: PDF_ANNOTATION_MODE_DISABLED,
        });
        await renderTask.promise;
        if (cancelled) return;

        const textContent = await page.getTextContent();
        if (cancelled) return;
        const textContainer = textLayerRef.current;
        if (textContainer) {
          textContainer.replaceChildren();
          textLayer = createPdfTextLayer({
            textContentSource: textContent,
            container: textContainer,
            viewport,
          });
          await textLayer.render();
        }
        if (!cancelled) onRenderStateChange?.("ready");
      } catch (error) {
        if (error?.name === "RenderingCancelledException" || cancelled) return;
        setRenderError("This page could not be rendered.");
        onRenderStateChange?.("error");
      }
    };
    void render();
    return () => {
      cancelled = true;
      renderTask?.cancel();
      textLayer?.cancel();
    };
  }, [
    containerSize.height,
    containerSize.width,
    pdfDocument,
    pageNumber,
    renderKey,
    zoomMode,
    zoomPercent,
    onRenderStateChange,
  ]);

  return (
    <div
      ref={containerRef}
      className="drawing-pdf-viewport"
      role="region"
      aria-label="Drawing PDF viewport"
      tabIndex="0"
    >
      {renderError ? (
        <div className="drawing-viewer-page-error" role="alert">
          <p>{renderError}</p>
          <Button size="sm" onClick={() => setRenderKey((value) => value + 1)}>
            Retry Page
          </Button>
        </div>
      ) : (
        <div className="drawing-pdf-page" aria-busy={!pdfDocument}>
          <canvas ref={canvasRef} aria-label={`${sheetLabel}, PDF page ${pageNumber}`}>
            {sheetLabel}, PDF page {pageNumber}
          </canvas>
          <div ref={textLayerRef} className="textLayer" aria-hidden="true" />
        </div>
      )}
    </div>
  );
}

export default PdfCanvasViewport;
