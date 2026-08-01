import {
  formatAttachmentDateTime,
  formatAttachmentFileSize,
} from "../../../utils/attachment";
import { formatDisplayDate } from "../../../utils/date";
import { drawingDisciplineLabel } from "../../../utils/drawing";


function DrawingMetadataPanel({
  sheet,
  revision,
  revisions,
  pageCount,
  onRevisionChange,
}) {
  if (!sheet || !revision) return null;
  return (
    <aside className="drawing-metadata-panel" aria-labelledby="drawing-details-title">
      <h2 id="drawing-details-title">Drawing Details</h2>
      <label htmlFor="drawing-viewer-revision">Revision history</label>
      <select
        id="drawing-viewer-revision"
        className="field-control"
        value={revision.id}
        onChange={(event) => onRevisionChange(Number(event.target.value))}
      >
        {revisions.map((item) => (
          <option key={item.id} value={item.id}>
            Rev {item.revision_code} - {item.is_current ? "Current" : "Superseded"}
          </option>
        ))}
      </select>

      <dl className="drawing-viewer-metadata">
        <div><dt>Sheet</dt><dd>{sheet.sheet_number}</dd></div>
        <div><dt>Title</dt><dd>{sheet.title}</dd></div>
        <div><dt>Discipline</dt><dd>{drawingDisciplineLabel(sheet.discipline)}</dd></div>
        <div><dt>Drawing set</dt><dd>{sheet.drawing_set_name}</dd></div>
        <div><dt>Revision</dt><dd>{revision.revision_code}</dd></div>
        <div><dt>Revision date</dt><dd>{formatDisplayDate(revision.revision_date)}</dd></div>
        <div><dt>Sequence</dt><dd>{revision.sequence_number}</dd></div>
        <div>
          <dt>Status</dt>
          <dd>{revision.is_current ? "Current Revision" : "Superseded Revision"}</dd>
        </div>
        <div><dt>Uploaded</dt><dd>{formatAttachmentDateTime(revision.created_at)}</dd></div>
        <div><dt>File size</dt><dd>{formatAttachmentFileSize(revision.size_bytes)}</dd></div>
        <div><dt>Pages</dt><dd>{pageCount}</dd></div>
        {!revision.is_current && (
          <>
            <div><dt>Superseded</dt><dd>{formatAttachmentDateTime(revision.superseded_at)}</dd></div>
            <div><dt>Successor record</dt><dd>{revision.superseded_by_revision_id || "Not recorded"}</dd></div>
          </>
        )}
        <div>
          <dt>Issue memberships</dt>
          <dd>{revision.issue_ids.length ? revision.issue_ids.join(", ") : "Not issued"}</dd>
        </div>
      </dl>
      <section aria-labelledby="drawing-revision-description-title">
        <h3 id="drawing-revision-description-title">Revision Description</h3>
        <p>{revision.description || "No revision description."}</p>
      </section>
    </aside>
  );
}

export default DrawingMetadataPanel;
