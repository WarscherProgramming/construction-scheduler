import { useState } from "react";

import DrawingSearchPanel from "../components/drawings/viewer/DrawingSearchPanel";
import DrawingViewerHeader from "../components/drawings/viewer/DrawingViewerHeader";
import DrawingViewerToolbar from "../components/drawings/viewer/DrawingViewerToolbar";
import DrawingViewerWorkspace from "../components/drawings/viewer/DrawingViewerWorkspace";
import ViewerStatusRegion from "../components/drawings/viewer/ViewerStatusRegion";
import Button from "../components/ui/Button";
import ProjectLayout from "../components/ui/ProjectLayout";
import useDrawingViewer from "../hooks/useDrawingViewer";


const LOADING_MESSAGES = {
  metadata: "Loading drawing metadata...",
  download: "Downloading authorized PDF...",
  parsing: "Preparing PDF pages...",
};


function ProjectDrawingViewerPage({
  projectId,
  projectName = "Project",
  sheetId,
  revisionId,
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const viewer = useDrawingViewer({
    projectId,
    sheetId,
    revisionId,
    onError: onRequestError,
  });
  const [showThumbnails, setShowThumbnails] = useState(true);
  const [showMetadata, setShowMetadata] = useState(true);
  const [renderStatus, setRenderStatus] = useState("idle");

  const backToRegister = () => onNavigate("projectDrawings", projectId);
  const navigateRevision = (nextRevisionId) => {
    onNavigate("drawingViewer", projectId, {
      sheetId,
      revisionId: nextRevisionId,
    });
  };
  const navigateSheet = (sheet) => {
    if (!sheet?.current_revision) return;
    onNavigate("drawingViewer", projectId, {
      sheetId: sheet.id,
      revisionId: sheet.current_revision.id,
    });
  };

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectDrawings"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="drawing-viewer-page"
    >
      <DrawingViewerHeader
        sheet={viewer.sheet}
        revision={viewer.revision}
        previousSheet={viewer.previousSheet}
        nextSheet={viewer.nextSheet}
        onBack={backToRegister}
        onPreviousSheet={() => navigateSheet(viewer.previousSheet)}
        onNextSheet={() => navigateSheet(viewer.nextSheet)}
        onDownload={viewer.download}
        canDownload={viewer.canDownload}
      />

      {viewer.phase === "error" ? (
        <section className="drawing-viewer-load-state" role="alert" aria-labelledby="drawing-viewer-error-title">
          <h2 id="drawing-viewer-error-title">Unable to display this drawing</h2>
          <p>{viewer.error?.message}</p>
          <div>
            <Button variant="primary" onClick={viewer.retry}>Retry</Button>
            {viewer.canDownload && <Button onClick={viewer.download}>Download PDF</Button>}
            <Button onClick={backToRegister}>Return to Drawing Register</Button>
          </div>
        </section>
      ) : viewer.phase !== "ready" ? (
        <section className="drawing-viewer-load-state" role="status" aria-live="polite">
          <span className="loading-state__spinner" aria-hidden="true" />
          <p>{LOADING_MESSAGES[viewer.phase]}</p>
        </section>
      ) : (
        <>
          <DrawingViewerToolbar
            currentPage={viewer.currentPage}
            pageCount={viewer.pageCount}
            zoomMode={viewer.zoomMode}
            zoomPercent={viewer.zoomPercent}
            onPageChange={viewer.setCurrentPage}
            onZoomIn={viewer.zoomIn}
            onZoomOut={viewer.zoomOut}
            onResetZoom={viewer.resetZoom}
            onFitWidth={viewer.fitWidth}
            onFitPage={viewer.fitPage}
            showThumbnails={showThumbnails}
            showMetadata={showMetadata}
            onToggleThumbnails={() => setShowThumbnails((value) => !value)}
            onToggleMetadata={() => setShowMetadata((value) => !value)}
          />
          <DrawingSearchPanel
            key={viewer.revision.id}
            search={viewer.search}
            onSearch={viewer.searchPdf}
            onPrevious={() => viewer.moveSearchMatch(-1)}
            onNext={() => viewer.moveSearchMatch(1)}
            onClear={viewer.clearSearch}
          />
          <DrawingViewerWorkspace
            viewer={viewer}
            projectId={projectId}
            showThumbnails={showThumbnails}
            showMetadata={showMetadata}
            onRevisionChange={navigateRevision}
            onNavigate={onNavigate}
            onError={onRequestError}
            onRenderStateChange={setRenderStatus}
          />
        </>
      )}

      <ViewerStatusRegion
        phase={viewer.phase}
        renderStatus={renderStatus}
        currentPage={viewer.currentPage}
        pageCount={viewer.pageCount}
      />
      <p className="drawing-viewer-accessibility-note">
        Viewer controls are accessible; the accessibility of drawing content depends on the uploaded source PDF.
      </p>
    </ProjectLayout>
  );
}

export default ProjectDrawingViewerPage;
