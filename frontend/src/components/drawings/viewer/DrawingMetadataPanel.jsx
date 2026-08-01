import { useState } from "react";

import RelationshipPanel from "../../relationships/RelationshipPanel";
import Button from "../../ui/Button";
import Icon from "../../ui/Icon";
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
  projectId,
  onRevisionChange,
  onNavigate,
  onError,
}) {
  const [showRelationships, setShowRelationships] = useState(false);
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
      <section
        className="drawing-metadata-relationships"
        aria-labelledby="drawing-relationships-title"
      >
        <div className="drawing-metadata-relationships__header">
          <h3 id="drawing-relationships-title">Related Records</h3>
          <Button
            size="sm"
            aria-expanded={showRelationships}
            aria-controls="drawing-revision-relationships"
            onClick={() => setShowRelationships((value) => !value)}
          >
            <Icon name="link" size={15} />
            {showRelationships ? "Close" : "Relationships"}
          </Button>
        </div>
        {showRelationships && (
          <div id="drawing-revision-relationships">
            <RelationshipPanel
              key={revision.id}
              projectId={projectId}
              entityType="drawing_revision"
              entityId={revision.id}
              title={`Revision ${revision.revision_code} Relationships`}
              compact
              onNavigate={onNavigate}
              onError={onError}
            />
          </div>
        )}
      </section>
    </aside>
  );
}

export default DrawingMetadataPanel;
