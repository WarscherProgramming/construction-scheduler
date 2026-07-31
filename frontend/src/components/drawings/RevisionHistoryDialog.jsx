import {
  formatAttachmentDateTime,
  formatAttachmentFileSize,
} from "../../utils/attachment";
import { formatDisplayDate } from "../../utils/date";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import DrawingDialog from "./DrawingDialog";


function RevisionHistoryDialog({
  sheet,
  revisions,
  isLoading,
  activeOperations,
  onDownload,
  onClose,
}) {
  return (
    <DrawingDialog
      title={`Revision History - ${sheet.sheet_number}`}
      eyebrow={sheet.title}
      onClose={onClose}
      actions={<Button onClick={onClose}>Close</Button>}
    >
      {isLoading ? (
        <p role="status">Loading revision history...</p>
      ) : revisions.length === 0 ? (
        <p>No drawing revisions are available.</p>
      ) : (
        <ol className="drawing-revision-history">
          {revisions.map((revision) => {
            const downloading = activeOperations.includes(
              `download:${revision.id}`
            );
            return (
              <li key={revision.id}>
                <div className="drawing-revision-history__heading">
                  <div>
                    <strong>Revision {revision.revision_code}</strong>
                    <span>Sequence {revision.sequence_number}</span>
                  </div>
                  <span
                    className={`drawing-revision-state drawing-revision-state--${
                      revision.is_current ? "current" : "superseded"
                    }`}
                  >
                    <Icon
                      name={revision.is_current ? "check-circle" : "info"}
                      size={15}
                    />
                    {revision.is_current
                      ? "Current Revision"
                      : "Superseded"}
                  </span>
                </div>
                <dl className="drawing-revision-meta">
                  <div>
                    <dt>Revision date</dt>
                    <dd>{formatDisplayDate(revision.revision_date)}</dd>
                  </div>
                  <div>
                    <dt>Uploaded</dt>
                    <dd>{formatAttachmentDateTime(revision.created_at)}</dd>
                  </div>
                  <div>
                    <dt>File</dt>
                    <dd>{revision.original_filename}</dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{formatAttachmentFileSize(revision.size_bytes)}</dd>
                  </div>
                  {!revision.is_current && (
                    <>
                      <div>
                        <dt>Superseded</dt>
                        <dd>
                          {formatAttachmentDateTime(
                            revision.superseded_at
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Successor</dt>
                        <dd>
                          Revision record{" "}
                          {revision.superseded_by_revision_id}
                        </dd>
                      </div>
                    </>
                  )}
                  <div>
                    <dt>Issues</dt>
                    <dd>
                      {revision.issue_ids.length
                        ? revision.issue_ids.join(", ")
                        : "Not issued"}
                    </dd>
                  </div>
                </dl>
                {revision.description && <p>{revision.description}</p>}
                <Button
                  size="sm"
                  disabled={downloading}
                  onClick={() => onDownload(revision)}
                  aria-label={`Download ${sheet.sheet_number} revision ${revision.revision_code}`}
                >
                  <Icon name="download" size={15} />
                  {downloading ? "Downloading..." : "Download"}
                </Button>
              </li>
            );
          })}
        </ol>
      )}
    </DrawingDialog>
  );
}

export default RevisionHistoryDialog;
