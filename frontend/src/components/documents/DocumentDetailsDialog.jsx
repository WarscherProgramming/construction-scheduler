import { useEffect, useId, useRef } from "react";

import {
  formatAttachmentDateTime,
  formatAttachmentFileSize,
} from "../../utils/attachment";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function DocumentDetailsDialog({
  documentRecord,
  folderLocation,
  isDownloading = false,
  onDownload,
  onRelationships,
  onClose,
}) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const closeRef = useRef(null);

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
  );
}

export default DocumentDetailsDialog;
