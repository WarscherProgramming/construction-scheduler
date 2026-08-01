import Button from "../../ui/Button";
import Icon from "../../ui/Icon";


function DrawingViewerHeader({
  sheet,
  revision,
  previousSheet,
  nextSheet,
  onBack,
  onPreviousSheet,
  onNextSheet,
  onDownload,
  canDownload,
}) {
  return (
    <header className="drawing-viewer-header">
      <div>
        <Button size="sm" variant="ghost" onClick={onBack}>
          <Icon name="chevron-left" size={16} />
          Drawing Register
        </Button>
        <p className="drawing-viewer-header__eyebrow">
          {sheet?.drawing_set_name || "Drawing set"}
        </p>
        <h1>
          {sheet ? `${sheet.sheet_number} - ${sheet.title}` : "Drawing Viewer"}
        </h1>
        {revision && (
          <p className="drawing-viewer-header__revision">
            Revision {revision.revision_code} · {revision.is_current ? "Current Revision" : "Superseded Revision"}
          </p>
        )}
      </div>
      <div className="drawing-viewer-header__actions">
        <Button
          size="sm"
          disabled={!previousSheet}
          onClick={onPreviousSheet}
          aria-label="View previous drawing sheet"
        >
          <Icon name="chevron-left" size={15} />
          Previous Sheet
        </Button>
        <Button
          size="sm"
          disabled={!nextSheet}
          onClick={onNextSheet}
          aria-label="View next drawing sheet"
        >
          Next Sheet
          <Icon name="chevron-right" size={15} />
        </Button>
        <Button size="sm" disabled={!canDownload} onClick={onDownload}>
          <Icon name="download" size={15} />
          Download PDF
        </Button>
      </div>
    </header>
  );
}

export default DrawingViewerHeader;
