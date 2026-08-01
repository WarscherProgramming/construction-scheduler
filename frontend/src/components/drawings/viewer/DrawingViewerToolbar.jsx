import { useRef } from "react";

import Button from "../../ui/Button";
import Icon from "../../ui/Icon";


function DrawingViewerToolbar({
  currentPage,
  pageCount,
  zoomMode,
  zoomPercent,
  onPageChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onFitWidth,
  onFitPage,
  showThumbnails,
  showMetadata,
  onToggleThumbnails,
  onToggleMetadata,
}) {
  const pageInputRef = useRef(null);

  const submitPage = (event) => {
    event.preventDefault();
    const nextPage = Math.min(
      pageCount,
      Math.max(1, Number(pageInputRef.current?.value) || 1)
    );
    onPageChange(nextPage);
    if (pageInputRef.current) pageInputRef.current.value = String(nextPage);
  };

  const zoomLabel =
    zoomMode === "percent"
      ? `${zoomPercent}%`
      : zoomMode === "fit-page"
        ? "Fit page"
        : "Fit width";

  return (
    <div className="drawing-viewer-toolbar" role="toolbar" aria-label="PDF viewer controls">
      <div className="drawing-viewer-toolbar__group">
        <Button
          size="sm"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(1)}
          aria-label="First page"
        >
          First
        </Button>
        <Button
          size="sm"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          aria-label="Previous page"
        >
          <Icon name="chevron-left" size={15} />
        </Button>
        <form onSubmit={submitPage} className="drawing-viewer-page-form">
          <label htmlFor="drawing-viewer-page">Page</label>
          <input
            id="drawing-viewer-page"
            key={currentPage}
            ref={pageInputRef}
            type="number"
            min="1"
            max={pageCount || 1}
            defaultValue={currentPage}
          />
          <span>of {pageCount || 0}</span>
          <Button size="sm" type="submit">Go</Button>
        </form>
        <Button
          size="sm"
          disabled={currentPage >= pageCount}
          onClick={() => onPageChange(currentPage + 1)}
          aria-label="Next page"
        >
          <Icon name="chevron-right" size={15} />
        </Button>
        <Button
          size="sm"
          disabled={currentPage >= pageCount}
          onClick={() => onPageChange(pageCount)}
          aria-label="Last page"
        >
          Last
        </Button>
      </div>

      <div className="drawing-viewer-toolbar__group" aria-label="Zoom controls">
        <Button size="sm" onClick={onZoomOut} aria-label="Zoom out">
          <Icon name="zoom-out" size={16} />
        </Button>
        <output className="drawing-viewer-zoom" aria-label={`Zoom ${zoomLabel}`}>
          {zoomLabel}
        </output>
        <Button size="sm" onClick={onZoomIn} aria-label="Zoom in">
          <Icon name="zoom-in" size={16} />
        </Button>
        <Button size="sm" onClick={onResetZoom}>100%</Button>
        <Button size="sm" onClick={onFitWidth}>Fit Width</Button>
        <Button size="sm" onClick={onFitPage}>Fit Page</Button>
      </div>

      <div className="drawing-viewer-toolbar__group drawing-viewer-toolbar__panels">
        <Button
          size="sm"
          aria-pressed={showThumbnails}
          onClick={onToggleThumbnails}
        >
          Pages
        </Button>
        <Button
          size="sm"
          aria-pressed={showMetadata}
          onClick={onToggleMetadata}
        >
          Details
        </Button>
      </div>
    </div>
  );
}

export default DrawingViewerToolbar;
