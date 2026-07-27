import { useEffect, useId, useRef, useState } from "react";

import useAttachments from "../hooks/useAttachments";
import {
  ATTACHMENT_ACCEPT,
  formatAttachmentDateTime,
  formatAttachmentFileSize,
  getAttachmentFileType,
  getSafeAttachmentFilename,
  isAttachmentPreviewEligible,
} from "../utils/attachment";
import Button from "./ui/Button";
import ConfirmDialog from "./ui/ConfirmDialog";
import Icon from "./ui/Icon";


function hasDraggedFiles(dataTransfer) {
  return Array.from(dataTransfer?.types || []).includes("Files");
}


function AttachmentPanel({
  projectId,
  parentType,
  parentId,
  title = "Attachments",
  canUpload = true,
  canDelete = true,
  compact = false,
  onCountChange,
  onError,
}) {
  const inputId = useId();
  const headingId = useId();
  const inputRef = useRef(null);
  const headingRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const isPersistentParent = Boolean(projectId && parentType && parentId);
  const {
    attachments,
    isLoading,
    isUploading,
    uploadingFilename,
    uploadResults,
    deletingIds,
    downloadingIds,
    error,
    refresh,
    uploadFiles,
    downloadAttachment,
    deleteAttachment,
    clearError,
  } = useAttachments({
    projectId,
    parentType,
    parentId,
    enabled: isPersistentParent,
    onError,
  });

  useEffect(() => {
    if (isPersistentParent) {
      onCountChange?.(attachments.length);
    }
  }, [attachments.length, isPersistentParent, onCountChange]);

  if (!isPersistentParent) return null;

  const fileCountLabel = `${attachments.length} ${
    attachments.length === 1 ? "file" : "files"
  }`;

  const selectFiles = (files) => {
    if (!files?.length || isUploading) return;
    uploadFiles(files);
  };

  const handleDrop = (event) => {
    setIsDragging(false);
    if (!hasDraggedFiles(event.dataTransfer)) return;
    event.preventDefault();
    selectFiles(event.dataTransfer.files);
  };

  const handleDeleteConfirm = async () => {
    const attachment = pendingDelete;
    setPendingDelete(null);
    if (!attachment) return;

    const deleted = await deleteAttachment(attachment);
    if (deleted) {
      headingRef.current?.focus();
    }
  };

  return (
    <section
      className={`attachment-panel${
        compact ? " attachment-panel--compact" : ""
      }`}
      aria-labelledby={headingId}
    >
      <header className="attachment-panel__header">
        <div className="attachment-panel__heading">
          <Icon name="file-text" size={20} />
          <h2
            ref={headingRef}
            id={headingId}
            className="attachment-panel__title"
            tabIndex="-1"
          >
            {title}
          </h2>
        </div>
        <span
          className="attachment-panel__count"
          aria-label={`Attachment count: ${fileCountLabel}`}
        >
          {fileCountLabel}
        </span>
      </header>

      {canUpload && (
        <div className="attachment-panel__upload">
          <input
            ref={inputRef}
            id={inputId}
            className="visually-hidden"
            type="file"
            multiple
            accept={ATTACHMENT_ACCEPT}
            disabled={isUploading}
            onChange={(event) => {
              selectFiles(event.target.files);
              event.target.value = "";
            }}
          />
          <label
            htmlFor={inputId}
            className={`attachment-drop-zone${
              isDragging ? " attachment-drop-zone--active" : ""
            }${isUploading ? " attachment-drop-zone--disabled" : ""}`}
            role="button"
            tabIndex={isUploading ? -1 : 0}
            aria-disabled={isUploading}
            onKeyDown={(event) => {
              if (
                !isUploading &&
                (event.key === "Enter" || event.key === " ")
              ) {
                event.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragEnter={(event) => {
              if (hasDraggedFiles(event.dataTransfer)) {
                event.preventDefault();
                setIsDragging(true);
              }
            }}
            onDragOver={(event) => {
              if (hasDraggedFiles(event.dataTransfer)) {
                event.preventDefault();
                event.dataTransfer.dropEffect = "copy";
                setIsDragging(true);
              }
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) {
                setIsDragging(false);
              }
            }}
            onDrop={handleDrop}
          >
            <Icon name="plus" size={18} />
            <span className="attachment-drop-zone__text">
              <strong>
                {isUploading
                  ? `Uploading ${uploadingFilename || "file"}`
                  : isDragging
                    ? "Release files to upload"
                    : "Choose files"}
              </strong>
              <span>or drag files here, up to 25 MiB each</span>
            </span>
          </label>
        </div>
      )}

      <div
        className="attachment-panel__status"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {isUploading
          ? `Uploading ${uploadingFilename || "selected files"}`
          : ""}
      </div>

      {uploadResults.length > 0 && (
        <ul
          className="attachment-upload-results"
          aria-label="Upload results"
          aria-live="polite"
        >
          {uploadResults.map((result, index) => (
            <li
              key={`${result.filename}-${index}`}
              className={`attachment-upload-result attachment-upload-result--${result.status}`}
            >
              <span>{result.filename}</span>
              <span>{result.message}</span>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <div className="attachment-panel__error" role="alert">
          <span>{error.message}</span>
          <div className="attachment-panel__error-actions">
            {error.operation === "list" && (
              <Button size="sm" onClick={refresh}>
                <Icon name="refresh" size={15} />
                Retry
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={clearError}
              aria-label="Dismiss attachment error"
            >
              <Icon name="x" size={15} />
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="attachment-panel__loading" role="status">
          Loading attachments...
        </div>
      ) : attachments.length === 0 ? (
        <div className="attachment-panel__empty">
          <Icon name="file-text" size={24} />
          <span>No attachments yet.</span>
        </div>
      ) : (
        <ul className="attachment-list" aria-label={`${title} files`}>
          {attachments.map((attachment) => {
            const filename = getSafeAttachmentFilename(
              attachment.original_filename
            );
            const previewEligible = isAttachmentPreviewEligible(
              filename,
              attachment.mime_type
            );
            const isDownloading = downloadingIds.includes(attachment.id);
            const isDeleting = deletingIds.includes(attachment.id);

            return (
              <li key={attachment.id} className="attachment-list__item">
                <div className="attachment-list__details">
                  <span className="attachment-list__filename">
                    {filename}
                  </span>
                  <span className="attachment-list__metadata">
                    {getAttachmentFileType(
                      filename,
                      attachment.mime_type
                    )}
                    <span aria-hidden="true"> · </span>
                    {formatAttachmentFileSize(attachment.size_bytes)}
                    <span aria-hidden="true"> · </span>
                    {formatAttachmentDateTime(attachment.created_at)}
                  </span>
                </div>
                <div className="attachment-list__actions">
                  <Button
                    size="sm"
                    onClick={() => downloadAttachment(attachment)}
                    disabled={isDownloading}
                    aria-label={`${
                      previewEligible ? "Preview" : "Download"
                    } ${filename}`}
                  >
                    <Icon name="download" size={15} />
                    {isDownloading
                      ? "Opening..."
                      : previewEligible
                        ? "Preview"
                        : "Download"}
                  </Button>
                  {canDelete && (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => setPendingDelete(attachment)}
                      disabled={isDeleting}
                      aria-label={`Delete ${filename}`}
                    >
                      <Icon name="trash" size={15} />
                      {isDeleting ? "Deleting..." : "Delete"}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        destructive
        title={`Delete ${getSafeAttachmentFilename(
          pendingDelete?.original_filename
        )}?`}
        message="The file will be permanently removed. This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}

export default AttachmentPanel;
