import { useRef, useState } from "react";

import DocumentDetailsDialog from "../components/documents/DocumentDetailsDialog";
import DocumentFolderTree from "../components/documents/DocumentFolderTree";
import RelationshipPanel from "../components/relationships/RelationshipPanel";
import Button from "../components/ui/Button";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import useDocumentExplorer from "../hooks/useDocumentExplorer";
import {
  ATTACHMENT_ACCEPT,
  formatAttachmentDateTime,
  formatAttachmentFileSize,
  getAttachmentFileType,
} from "../utils/attachment";


function hasDraggedFiles(dataTransfer) {
  return Array.from(dataTransfer?.types || []).includes("Files");
}


function explorerErrorMessage(error) {
  if (error?.status === 403) {
    return "You do not have access to this project's documents.";
  }
  if (error?.status === 404) {
    return "This folder is no longer available.";
  }
  if (error?.status === 429) {
    return "Document requests are temporarily limited. Try again shortly.";
  }
  return error?.message || "The document explorer could not be loaded.";
}


function ProjectDocumentsPage({
  projectId,
  projectName = "Project",
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const fileInputRef = useRef(null);
  const locationHeadingRef = useRef(null);
  const folderNameRef = useRef(null);
  const [searchDraft, setSearchDraft] = useState("");
  const [showFolderForm, setShowFolderForm] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [folderPanelOpen, setFolderPanelOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [relationshipDocument, setRelationshipDocument] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const explorer = useDocumentExplorer({
    projectId,
    onError: onRequestError,
  });
  const data = explorer.explorer;
  const currentFolderId = explorer.query.folderId;
  const currentLocation = data?.current_folder?.name || "Project root";

  const selectFolder = (folderId) => {
    setFolderPanelOpen(false);
    setSelectedDocument(null);
    explorer.updateQuery({ folderId });
  };

  const selectFiles = (files) => {
    if (!files?.length || explorer.isUploading) return;
    void explorer.uploadFiles(files);
  };

  const handleFolderCreate = async (event) => {
    event.preventDefault();
    if (!folderName.trim()) return;
    const created = await explorer.createCurrentFolder(folderName);
    if (created) {
      setFolderName("");
      setShowFolderForm(false);
      locationHeadingRef.current?.focus();
    } else {
      folderNameRef.current?.focus();
    }
  };

  const handleDeleteConfirm = async () => {
    const documentRecord = pendingDelete;
    if (!documentRecord) return;
    const deleted = await explorer.removeDocument(documentRecord);
    if (deleted) {
      setPendingDelete(null);
      setSelectedDocument((current) =>
        current?.id === documentRecord.id ? null : current
      );
      setRelationshipDocument((current) =>
        current?.id === documentRecord.id ? null : current
      );
      locationHeadingRef.current?.focus();
    }
  };

  const folderLocationFor = (documentRecord) => {
    if (!documentRecord?.folder_id) return "Project root";
    const byId = new Map(
      explorer.folderTree.map((folder) => [folder.id, folder])
    );
    const names = [];
    let current = byId.get(documentRecord.folder_id);
    const seen = new Set();
    while (current && !seen.has(current.id) && names.length < 32) {
      seen.add(current.id);
      names.unshift(current.name);
      current = current.parent_folder_id
        ? byId.get(current.parent_folder_id)
        : null;
    }
    return names.length ? `Project root / ${names.join(" / ")}` : "Folder";
  };

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectDocuments"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="document-explorer-page"
    >
      <PageHeader
        title="Project Documents"
        subtitle="Browse project files, folders, and recent uploads."
        actions={
          <>
            <Button
              onClick={() => {
                setShowFolderForm((current) => !current);
                window.setTimeout(() => folderNameRef.current?.focus(), 0);
              }}
            >
              <Icon name="folder" size={17} />
              New Folder
            </Button>
            <Button
              variant="primary"
              disabled={explorer.isUploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <Icon name="upload" size={17} />
              {explorer.isUploading ? "Uploading..." : "Upload Files"}
            </Button>
          </>
        }
      />

      <input
        ref={fileInputRef}
        className="visually-hidden"
        type="file"
        multiple
        accept={ATTACHMENT_ACCEPT}
        aria-label="Choose documents to upload"
        disabled={explorer.isUploading}
        onChange={(event) => {
          selectFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {showFolderForm && (
        <form
          className="document-folder-form"
          aria-label={`Create folder in ${currentLocation}`}
          onSubmit={handleFolderCreate}
        >
          <label htmlFor="document-folder-name">Folder name</label>
          <input
            ref={folderNameRef}
            id="document-folder-name"
            className="field-control"
            required
            maxLength={255}
            value={folderName}
            onChange={(event) => setFolderName(event.target.value)}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={explorer.isCreatingFolder || !folderName.trim()}
          >
            {explorer.isCreatingFolder ? "Creating..." : "Create Folder"}
          </Button>
          <Button onClick={() => setShowFolderForm(false)}>Cancel</Button>
        </form>
      )}

      <section
        className={`document-upload-zone${
          isDragging ? " document-upload-zone--active" : ""
        }`}
        aria-label="Document upload area"
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
        onDrop={(event) => {
          setIsDragging(false);
          if (!hasDraggedFiles(event.dataTransfer)) return;
          event.preventDefault();
          selectFiles(event.dataTransfer.files);
        }}
      >
        <Icon name="upload" size={20} />
        <span>
          {isDragging
            ? "Release documents to upload"
            : `Drop documents into ${currentLocation}, or use Upload Files`}
        </span>
      </section>

      {explorer.uploadResults.length > 0 && (
        <section className="document-upload-queue" aria-labelledby="upload-results-title">
          <div className="document-upload-queue__header">
            <h2 id="upload-results-title">Upload results</h2>
            {explorer.failedUploadCount > 0 && (
              <Button
                size="sm"
                disabled={explorer.isUploading}
                onClick={explorer.retryFailedUploads}
              >
                <Icon name="refresh" size={15} />
                Retry Failed
              </Button>
            )}
          </div>
          <ul aria-live="polite">
            {explorer.uploadResults.map((result, index) => (
              <li key={`${result.filename}-${index}`}>
                <span>{result.filename}</span>
                <span>{result.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {explorer.operationError && (
        <div className="document-explorer-alert" role="alert">
          <span>{explorerErrorMessage(explorer.operationError)}</span>
          <Button
            size="sm"
            variant="ghost"
            aria-label="Dismiss document error"
            onClick={explorer.clearOperationError}
          >
            <Icon name="x" size={16} />
          </Button>
        </div>
      )}

      <div className="document-explorer-layout">
        <DocumentFolderTree
          folders={explorer.folderTree}
          activeFolderId={currentFolderId}
          isLoading={explorer.isNavigationLoading}
          isOpen={folderPanelOpen}
          onToggle={() => setFolderPanelOpen((current) => !current)}
          onSelect={selectFolder}
        />

        <div className="document-explorer-main">
          <nav className="document-breadcrumbs" aria-label="Document location">
            <button type="button" onClick={() => selectFolder(null)}>
              Project root
            </button>
            {(data?.breadcrumbs || []).map((folder) => (
              <span key={folder.id}>
                <Icon name="chevron-right" size={14} />
                <button
                  type="button"
                  aria-current={
                    folder.id === currentFolderId ? "location" : undefined
                  }
                  onClick={() => selectFolder(folder.id)}
                >
                  {folder.name}
                </button>
              </span>
            ))}
          </nav>

          <div className="document-explorer-toolbar">
            <form
              className="document-search"
              role="search"
              onSubmit={(event) => {
                event.preventDefault();
                explorer.updateQuery({ search: searchDraft.trim() });
              }}
            >
              <label className="visually-hidden" htmlFor="document-search">
                Search document metadata
              </label>
              <input
                id="document-search"
                className="field-control"
                type="search"
                maxLength={200}
                placeholder="Search filenames and metadata"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
              />
              <Button type="submit" aria-label="Search documents">
                <Icon name="search" size={17} />
              </Button>
              {explorer.query.search && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSearchDraft("");
                    explorer.updateQuery({ search: "" });
                  }}
                >
                  Clear
                </Button>
              )}
            </form>
            <label>
              <span>Type</span>
              <select
                className="field-control"
                value={explorer.query.documentType}
                onChange={(event) =>
                  explorer.updateQuery({
                    documentType: event.target.value,
                  })
                }
              >
                <option value="">All types</option>
                <option value="General">General</option>
                <option value="Drawing">Drawing</option>
                <option value="Report">Report</option>
                <option value="Specification">Specification</option>
                <option value="Photo">Photo</option>
              </select>
            </label>
            <label>
              <span>Format</span>
              <select
                className="field-control"
                value={explorer.query.extension}
                onChange={(event) =>
                  explorer.updateQuery({ extension: event.target.value })
                }
              >
                <option value="">All formats</option>
                <option value=".pdf">PDF</option>
                <option value=".jpg">JPEG</option>
                <option value=".png">PNG</option>
                <option value=".docx">Word</option>
                <option value=".xlsx">Excel</option>
                <option value=".csv">CSV</option>
              </select>
            </label>
            <label>
              <span>Sort</span>
              <select
                className="field-control"
                value={`${explorer.query.sort}:${explorer.query.order}`}
                onChange={(event) => {
                  const [sort, order] = event.target.value.split(":");
                  explorer.updateQuery({ sort, order });
                }}
              >
                <option value="name:asc">Name A-Z</option>
                <option value="name:desc">Name Z-A</option>
                <option value="updated_at:desc">Recently modified</option>
                <option value="created_at:desc">Recently uploaded</option>
                <option value="size_bytes:desc">Largest first</option>
                <option value="document_type:asc">Document type</option>
              </select>
            </label>
          </div>

          <h2
            ref={locationHeadingRef}
            className="document-location-heading"
            tabIndex="-1"
          >
            {currentLocation}
          </h2>

          {explorer.isLoading ? (
            <div className="document-explorer-state" role="status">
              Loading documents...
            </div>
          ) : explorer.error ? (
            <div className="document-explorer-state" role="alert">
              <Icon name="alert-triangle" size={22} />
              <p>{explorerErrorMessage(explorer.error)}</p>
              <Button onClick={explorer.refresh}>
                <Icon name="refresh" size={16} />
                Retry
              </Button>
            </div>
          ) : data ? (
            <>
              {data.folders.length === 0 &&
              data.documents.length === 0 ? (
                <div className="document-explorer-state">
                  <Icon name="folder" size={24} />
                  <p>
                    {explorer.query.search
                      ? "No documents match this search."
                      : "This folder is empty."}
                  </p>
                </div>
              ) : (
                <div className="document-list-wrap">
                  <table className="document-list">
                    <caption className="visually-hidden">
                      Folders and documents in {currentLocation}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Name</th>
                        <th scope="col">Type</th>
                        <th scope="col">Size</th>
                        <th scope="col">Modified</th>
                        <th scope="col">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.folders.map((folder) => (
                        <tr key={`folder-${folder.id}`}>
                          <th scope="row" data-label="Name">
                            <button
                              type="button"
                              className="document-name-button"
                              onClick={() => selectFolder(folder.id)}
                            >
                              <Icon name="folder" size={18} />
                              <span>{folder.name}</span>
                            </button>
                          </th>
                          <td data-label="Type">Folder</td>
                          <td data-label="Size">
                            {folder.document_count} documents
                          </td>
                          <td data-label="Modified">
                            {formatAttachmentDateTime(folder.updated_at)}
                          </td>
                          <td data-label="Actions">
                            <Button
                              size="sm"
                              onClick={() => selectFolder(folder.id)}
                              aria-label={`Open folder ${folder.name}`}
                            >
                              Open
                            </Button>
                          </td>
                        </tr>
                      ))}
                      {data.documents.map((documentRecord) => {
                        const isDownloading =
                          explorer.downloadingIds.includes(documentRecord.id);
                        const isDeleting =
                          explorer.deletingIds.includes(documentRecord.id);
                        return (
                          <tr key={`document-${documentRecord.id}`}>
                            <th scope="row" data-label="Name">
                              <button
                                type="button"
                                className="document-name-button"
                                onClick={() =>
                                  setSelectedDocument(documentRecord)
                                }
                              >
                                <Icon name="file-text" size={18} />
                                <span>{documentRecord.display_name}</span>
                              </button>
                            </th>
                            <td data-label="Type">
                              {getAttachmentFileType(
                                documentRecord.original_filename,
                                documentRecord.mime_type
                              )}
                            </td>
                            <td data-label="Size">
                              {formatAttachmentFileSize(
                                documentRecord.size_bytes
                              )}
                            </td>
                            <td data-label="Modified">
                              {formatAttachmentDateTime(
                                documentRecord.updated_at
                              )}
                            </td>
                            <td data-label="Actions">
                              <div className="document-row-actions">
                                <Button
                                  size="sm"
                                  onClick={() =>
                                    setSelectedDocument(documentRecord)
                                  }
                                  aria-label={`View details for ${documentRecord.display_name}`}
                                >
                                  Details
                                </Button>
                                <Button
                                  size="sm"
                                  disabled={isDownloading}
                                  onClick={() =>
                                    explorer.download(documentRecord)
                                  }
                                  aria-label={`Download ${documentRecord.display_name}`}
                                >
                                  <Icon name="download" size={15} />
                                  {isDownloading ? "Downloading..." : "Download"}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="danger"
                                  disabled={isDeleting}
                                  onClick={() =>
                                    setPendingDelete(documentRecord)
                                  }
                                  aria-label={`Remove ${documentRecord.display_name}`}
                                >
                                  <Icon name="trash" size={15} />
                                  {isDeleting ? "Removing..." : "Remove"}
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="document-pagination" aria-label="Document pages">
                <Button
                  size="sm"
                  disabled={data.pagination.offset === 0}
                  onClick={() =>
                    explorer.updateQuery({
                      offset: Math.max(
                        0,
                        data.pagination.offset - data.pagination.limit
                      ),
                    })
                  }
                >
                  Previous
                </Button>
                <span>
                  {data.pagination.total === 0
                    ? "0 documents"
                    : `${data.pagination.offset + 1}-${Math.min(
                        data.pagination.offset + data.documents.length,
                        data.pagination.total
                      )} of ${data.pagination.total} documents`}
                </span>
                <Button
                  size="sm"
                  disabled={!data.pagination.has_more}
                  onClick={() =>
                    explorer.updateQuery({
                      offset:
                        data.pagination.offset + data.pagination.limit,
                    })
                  }
                >
                  Next
                </Button>
              </div>
            </>
          ) : null}
        </div>
      </div>

      <section className="recent-documents" aria-labelledby="recent-documents-title">
        <div className="recent-documents__header">
          <h2 id="recent-documents-title">Recent Documents</h2>
          <span>Current project</span>
        </div>
        {explorer.isNavigationLoading ? (
          <p role="status">Loading recent documents...</p>
        ) : explorer.recentDocuments.length === 0 ? (
          <p>No recent documents.</p>
        ) : (
          <ul>
            {explorer.recentDocuments.map((documentRecord) => (
              <li key={documentRecord.id}>
                <button
                  type="button"
                  onClick={() => setSelectedDocument(documentRecord)}
                >
                  <Icon name="file-text" size={17} />
                  <span>{documentRecord.display_name}</span>
                  <time dateTime={documentRecord.created_at}>
                    {formatAttachmentDateTime(documentRecord.created_at)}
                  </time>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {relationshipDocument && (
        <div
          className="record-relationship-detail"
          role="region"
          aria-label={`Relationships for document ${relationshipDocument.display_name}`}
        >
          <RelationshipPanel
            projectId={projectId}
            entityType="document"
            entityId={relationshipDocument.id}
            title={`${relationshipDocument.display_name} Relationships`}
            onNavigate={onNavigate}
            onError={onRequestError}
          />
        </div>
      )}

      <DocumentDetailsDialog
        documentRecord={selectedDocument}
        folderLocation={folderLocationFor(selectedDocument)}
        isDownloading={
          Boolean(selectedDocument) &&
          explorer.downloadingIds.includes(selectedDocument.id)
        }
        onDownload={explorer.download}
        onRelationships={(documentRecord) => {
          setSelectedDocument(null);
          setRelationshipDocument(documentRecord);
        }}
        onClose={() => setSelectedDocument(null)}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        destructive
        title={`Remove ${pendingDelete?.display_name || "document"}?`}
        message="This document will be removed from the active project document list. It will not be permanently erased."
        confirmLabel={
          pendingDelete &&
          explorer.deletingIds.includes(pendingDelete.id)
            ? "Removing..."
            : "Remove Document"
        }
        confirmDisabled={
          Boolean(pendingDelete) &&
          explorer.deletingIds.includes(pendingDelete.id)
        }
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          if (
            !pendingDelete ||
            !explorer.deletingIds.includes(pendingDelete.id)
          ) {
            setPendingDelete(null);
          }
        }}
      />
    </ProjectLayout>
  );
}

export default ProjectDocumentsPage;
