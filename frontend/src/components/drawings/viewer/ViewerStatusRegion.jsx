const PHASE_MESSAGES = {
  metadata: "Loading drawing metadata...",
  download: "Downloading authorized PDF...",
  parsing: "Preparing PDF pages...",
  ready: "Drawing ready.",
};


function ViewerStatusRegion({ phase, renderStatus, currentPage, pageCount }) {
  const message =
    phase === "ready" && renderStatus === "rendering"
      ? `Rendering page ${currentPage}...`
      : phase === "ready" && renderStatus === "ready"
        ? `Page ${currentPage} of ${pageCount} displayed.`
        : PHASE_MESSAGES[phase] || "";
  return (
    <p className="visually-hidden" role="status" aria-live="polite">
      {message}
    </p>
  );
}

export default ViewerStatusRegion;
