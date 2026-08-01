import DrawingMetadataPanel from "./DrawingMetadataPanel";
import DrawingThumbnailRail from "./DrawingThumbnailRail";
import PdfCanvasViewport from "./PdfCanvasViewport";


function isTypingTarget(target) {
  return target instanceof HTMLElement && Boolean(
    target.closest("input, textarea, select, button, [contenteditable='true']")
  );
}


function DrawingViewerWorkspace({
  viewer,
  showThumbnails,
  showMetadata,
  onRevisionChange,
  onRenderStateChange,
}) {
  const handleKeyDown = (event) => {
    if (isTypingTarget(event.target)) return;
    let handled = true;
    if (event.key === "ArrowLeft" || event.key === "PageUp") {
      viewer.setCurrentPage(viewer.currentPage - 1);
    } else if (event.key === "ArrowRight" || event.key === "PageDown") {
      viewer.setCurrentPage(viewer.currentPage + 1);
    } else if (event.key === "Home") {
      viewer.setCurrentPage(1);
    } else if (event.key === "End") {
      viewer.setCurrentPage(viewer.pageCount);
    } else if (event.key === "+" || event.key === "=") {
      viewer.zoomIn();
    } else if (event.key === "-") {
      viewer.zoomOut();
    } else if (event.key === "0") {
      viewer.resetZoom();
    } else if (event.key.toLowerCase() === "f") {
      viewer.fitWidth();
    } else {
      handled = false;
    }
    if (handled) event.preventDefault();
  };

  return (
    <div
      className={`drawing-viewer-workspace${showThumbnails ? " has-thumbnails" : ""}${showMetadata ? " has-metadata" : ""}`}
      onKeyDown={handleKeyDown}
      aria-label="Drawing viewer workspace"
    >
      {showThumbnails && (
        <DrawingThumbnailRail
          pdfDocument={viewer.pdfDocument}
          pageCount={viewer.pageCount}
          currentPage={viewer.currentPage}
          onSelect={viewer.setCurrentPage}
        />
      )}
      <PdfCanvasViewport
        pdfDocument={viewer.pdfDocument}
        pageNumber={viewer.currentPage}
        zoomMode={viewer.zoomMode}
        zoomPercent={viewer.zoomPercent}
        sheetLabel={`${viewer.sheet.sheet_number} ${viewer.sheet.title}`}
        onRenderStateChange={onRenderStateChange}
      />
      {showMetadata && (
        <DrawingMetadataPanel
          sheet={viewer.sheet}
          revision={viewer.revision}
          revisions={viewer.revisions}
          pageCount={viewer.pageCount}
          onRevisionChange={onRevisionChange}
        />
      )}
    </div>
  );
}

export default DrawingViewerWorkspace;
