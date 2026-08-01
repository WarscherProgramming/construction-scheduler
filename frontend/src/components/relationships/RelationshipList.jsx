import RelationshipItem from "./RelationshipItem";


function RelationshipList({
  relationships,
  deletingIds,
  canDelete,
  onNavigate,
  onRemove,
  label,
}) {
  return (
    <ul className="relationship-list" aria-label={label}>
      {relationships.map((relationship) => (
        <RelationshipItem
          key={relationship.id}
          relationship={relationship}
          isDeleting={deletingIds.includes(relationship.id)}
          canDelete={canDelete}
          onNavigate={onNavigate}
          onRemove={onRemove}
        />
      ))}
    </ul>
  );
}

export default RelationshipList;
