import { useId, useRef, useState } from "react";

import useRelationships from "../../hooks/useRelationships";
import { navigateToRelationship } from "../../utils/relationships";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import Icon from "../ui/Icon";
import CreateRelationshipDialog from "./CreateRelationshipDialog";
import RelationshipList from "./RelationshipList";


function RelationshipPanel({
  projectId,
  entityType,
  entityId,
  title = "Relationships",
  canCreate = true,
  canDelete = true,
  compact = false,
  onNavigate,
  onError,
}) {
  const headingId = useId();
  const headingRef = useRef(null);
  const [showCreate, setShowCreate] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const isPersistentEntity = Boolean(projectId && entityType && entityId);
  const {
    relationships,
    total,
    hasMore,
    isLoading,
    isCreating,
    deletingIds,
    error,
    refresh,
    loadMore,
    createRelationship,
    deleteRelationship,
    clearError,
  } = useRelationships({
    projectId,
    entityType,
    entityId,
    enabled: isPersistentEntity,
    onError,
  });

  if (!isPersistentEntity) return null;

  const handleDeleteConfirm = async () => {
    const relationship = pendingDelete;
    setPendingDelete(null);
    if (relationship && (await deleteRelationship(relationship))) {
      headingRef.current?.focus();
    }
  };

  return (
    <section
      className={`relationship-panel${
        compact ? " relationship-panel--compact" : ""
      }`}
      aria-labelledby={headingId}
    >
      <header className="relationship-panel__header">
        <div className="relationship-panel__heading">
          <Icon name="link" size={20} />
          <h2 ref={headingRef} id={headingId} tabIndex="-1">
            {title}
          </h2>
        </div>
        <div className="relationship-panel__header-actions">
          <span aria-label={`Relationship count: ${total}`}>
            {total} {total === 1 ? "link" : "links"}
          </span>
          {canCreate && (
            <Button size="sm" variant="primary" onClick={() => setShowCreate(true)}>
              <Icon name="plus" size={15} />
              Add Relationship
            </Button>
          )}
        </div>
      </header>

      {error?.operation === "list" && (
        <div className="relationship-panel__error" role="alert">
          <span>{error.message}</span>
          <div>
            <Button size="sm" onClick={refresh}>
              <Icon name="refresh" size={15} />
              Retry
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={clearError}
              aria-label="Dismiss relationship error"
            >
              <Icon name="x" size={15} />
              Dismiss
            </Button>
          </div>
        </div>
      )}
      {error && error.operation !== "list" && !showCreate && (
        <div className="relationship-panel__error" role="alert">
          <span>{error.message}</span>
          <Button size="sm" variant="ghost" onClick={clearError}>
            <Icon name="x" size={15} />
            Dismiss
          </Button>
        </div>
      )}

      {isLoading && relationships.length === 0 ? (
        <div className="relationship-panel__state" role="status">
          Loading relationships...
        </div>
      ) : relationships.length === 0 ? (
        <div className="relationship-panel__state">
          <Icon name="link" size={24} />
          <span>No relationships yet.</span>
        </div>
      ) : (
        <RelationshipList
          relationships={relationships}
          deletingIds={deletingIds}
          canDelete={canDelete}
          label={`${title} list`}
          onNavigate={(entity) =>
            navigateToRelationship(entity, onNavigate, projectId)
          }
          onRemove={setPendingDelete}
        />
      )}

      {hasMore && (
        <Button size="sm" disabled={isLoading} onClick={loadMore}>
          {isLoading ? "Loading..." : "Load More"}
        </Button>
      )}

      {showCreate && (
        <CreateRelationshipDialog
          projectId={projectId}
          entityType={entityType}
          entityId={entityId}
          relationships={relationships}
          isCreating={isCreating}
          mutationError={error?.operation === "create" ? error : null}
          onCreate={createRelationship}
          onClose={() => {
            setShowCreate(false);
            clearError();
          }}
          onError={onError}
        />
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        destructive
        title={`Remove relationship to ${
          pendingDelete?.related?.identifier || "this record"
        }?`}
        message="The related record will remain unchanged."
        confirmLabel="Remove Relationship"
        confirmDisabled={
          Boolean(pendingDelete) && deletingIds.includes(pendingDelete.id)
        }
        onConfirm={handleDeleteConfirm}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}

export default RelationshipPanel;
