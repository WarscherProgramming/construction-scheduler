import { formatAttachmentDateTime } from "../../utils/attachment";
import { RELATIONSHIP_ENTITY_LABELS } from "../../utils/relationships";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function RelationshipItem({
  relationship,
  isDeleting,
  canDelete,
  onNavigate,
  onRemove,
}) {
  const related = relationship.related;
  const entityLabel =
    RELATIONSHIP_ENTITY_LABELS[related.type] || "Related record";
  const recordLabel = `${entityLabel} ${related.identifier}`;

  return (
    <li className="relationship-list__item">
      <div className="relationship-list__content">
        <span className="relationship-list__relation">
          {relationship.relationship_label}
        </span>
        <div className="relationship-list__identity">
          <span>{entityLabel}</span>
          <strong>{related.identifier}</strong>
        </div>
        <p>{related.title}</p>
        <div className="relationship-list__metadata">
          {related.status && <span>Status: {related.status}</span>}
          {!related.available && <span>Record unavailable</span>}
          <span>
            Linked {formatAttachmentDateTime(relationship.created_at)}
          </span>
        </div>
      </div>
      <div className="relationship-list__actions">
        {related.available && related.route && (
          <Button
            size="sm"
            onClick={() => onNavigate(related)}
            aria-label={`Open ${recordLabel}`}
          >
            <Icon name="arrow-right" size={15} />
            Open
          </Button>
        )}
        {canDelete && (
          <Button
            size="sm"
            variant="danger"
            disabled={isDeleting}
            onClick={() => onRemove(relationship)}
            aria-label={`Remove relationship to ${recordLabel}`}
          >
            <Icon name="trash" size={15} />
            {isDeleting ? "Removing..." : "Remove"}
          </Button>
        )}
      </div>
    </li>
  );
}

export default RelationshipItem;
