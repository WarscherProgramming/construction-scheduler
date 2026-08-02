import { Fragment, useEffect, useId, useRef, useState } from "react";

import {
  formatAttachmentDateTime,
  formatAttachmentFileSize,
} from "../../utils/attachment";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import Icon from "../ui/Icon";
import useDocumentExtraction from "../../hooks/useDocumentExtraction";
import {
  extractionMethodLabel,
  extractionStatusLabel,
} from "../../utils/documentSearch";


function DocumentDetailsDialog({
  documentRecord,
  projectId,
  folderLocation,
  isDownloading = false,
  onDownload,
  onRelationships,
  onOpenSearch,
  onExtractionUpdate,
  onError,
  onClose,
}) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const [confirmReprocess, setConfirmReprocess] = useState(false);
  const extraction = useDocumentExtraction({
    projectId,
    documentId: documentRecord?.id,
    initialExtraction: documentRecord?.extraction,
    load: false,
    onError,
    onUpdate: onExtractionUpdate,
  });

  useEffect(() => {
    if (!documentRecord) return undefined;
    const previouslyFocused = document.activeElement;
    closeRef.current?.focus();
    return () => {
      if (previouslyFocused instanceof HTMLElement) {
        previouslyFocused.focus();
      }
    };
  }, [documentRecord]);

  if (!documentRecord) return null;

  const extractionRecord = extraction.extraction || documentRecord.extraction;
  const runReprocess = async () => {
    setConfirmReprocess(false);
    await extraction.reprocess();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable =
      dialogRef.current?.querySelectorAll("button:not(:disabled)") || [];
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const details = [
    ["Display name", documentRecord.display_name],
    ["Original filename", documentRecord.original_filename],
    ["Folder", folderLocation],
    ["Document type", documentRecord.document_type],
    ["MIME type", documentRecord.mime_type],
    ["Extension", documentRecord.extension],
    ["Size", formatAttachmentFileSize(documentRecord.size_bytes)],
    ["Version", String(documentRecord.version)],
    ["Status", documentRecord.status],
    ["Uploaded", formatAttachmentDateTime(documentRecord.created_at)],
    ["Modified", formatAttachmentDateTime(documentRecord.updated_at)],
  ];

  return (
    <Fragment>
      <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog document-details-dialog"
        onKeyDown={handleKeyDown}
      >
        <div className="document-details-dialog__header">
          <div>
            <p className="document-details-dialog__eyebrow">Document details</p>
            <h2 id={titleId}>{documentRecord.display_name}</h2>
          </div>
          <Button
            ref={closeRef}
            size="sm"
            variant="ghost"
            aria-label="Close document details"
            onClick={onClose}
          >
            <Icon name="x" size={18} />
          </Button>
        </div>
        <dl className="document-details-list">
          {details.map(([label, value]) => (
            <div key={label} className="document-details-list__item">
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <section className="document-extraction-details" aria-labelledby={`${titleId}-extraction`}>
          <div className="document-extraction-details__header">
            <h3 id={`${titleId}-extraction`}>Searchable Text</h3>
            <span>{extractionStatusLabel(extractionRecord)}</span>
          </div>
          <dl>
            <div>
              <dt>Text source</dt>
              <dd>{extractionMethodLabel(extractionRecord?.extraction_method)}</dd>
            </div>
            <div>
              <dt>Pages processed</dt>
              <dd>{extractionRecord?.pages_processed ?? 0}</dd>
            </div>
          </dl>
          {extractionRecord?.failure_message && (
            <p>{extractionRecord.failure_message}</p>
          )}
          {extraction.error && <p role="alert">{extraction.error.message}</p>}
          <div className="document-extraction-details__actions">
            <Button size="sm" onClick={() => onOpenSearch(documentRecord)}>
              <Icon name="search" size={15} />
              Open Search
            </Button>
            <Button
              size="sm"
              disabled={
                extraction.isReprocessing || !extractionRecord?.retry_eligible
              }
              onClick={() => {
                if (extractionRecord?.searchable) setConfirmReprocess(true);
                else void runReprocess();
              }}
            >
              <Icon name="refresh" size={15} />
              {extraction.isReprocessing ? "Queueing..." : "Reprocess Text"}
            </Button>
          </div>
        </section>
        <div className="dialog__actions">
          <Button onClick={onClose}>Close</Button>
          <Button onClick={() => onRelationships(documentRecord)}>
            <Icon name="link" size={16} />
            Relationships
          </Button>
          <Button
            variant="primary"
            disabled={isDownloading}
            onClick={() => onDownload(documentRecord)}
          >
            <Icon name="download" size={16} />
            {isDownloading ? "Downloading..." : "Download"}
          </Button>
        </div>
      </div>
      </div>
      <ConfirmDialog
        open={confirmReprocess}
        title="Reprocess searchable text?"
        message="Current search results remain available until replacement processing succeeds."
        confirmLabel="Reprocess Text"
        onConfirm={() => void runReprocess()}
        onCancel={() => setConfirmReprocess(false)}
      />
    </Fragment>
  );
}

export default DocumentDetailsDialog;
