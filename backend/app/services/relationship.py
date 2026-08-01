from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entity_relationship import EntityRelationship
from app.schemas.relationship import EntityRelationshipCreate
from app.services.relationship_resolver import (
    resolve_entity_summaries,
    resolve_relationship_entity,
)
from app.services.relationship_rules import (
    RELATIONSHIP_DEFINITIONS,
    SYMMETRIC_RELATIONSHIP_TYPES,
    canonicalize_relationship,
    is_allowed_relationship,
    is_symmetric_relationship,
    perspective_label,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_relationship_rule(
    source_type: str,
    relationship_type: str,
    target_type: str,
) -> None:
    if relationship_type not in RELATIONSHIP_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported relationship type",
        )
    if not is_allowed_relationship(
        source_type,
        relationship_type,
        target_type,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Relationship type is not allowed for these entities",
        )


def _relationship_references(
    relationships: list[EntityRelationship],
) -> set[tuple[str, int]]:
    return {
        reference
        for relationship in relationships
        for reference in (
            (relationship.source_type, relationship.source_id),
            (relationship.target_type, relationship.target_id),
        )
    }


def _serialize_relationship(
    relationship: EntityRelationship,
    summaries: dict,
    perspective_type: str,
    perspective_id: int,
) -> dict:
    source = summaries[(relationship.source_type, relationship.source_id)]
    target = summaries[(relationship.target_type, relationship.target_id)]
    if is_symmetric_relationship(relationship.relationship_type):
        direction = "symmetric"
        related = (
            target
            if (
                relationship.source_type == perspective_type
                and relationship.source_id == perspective_id
            )
            else source
        )
    elif (
        relationship.source_type == perspective_type
        and relationship.source_id == perspective_id
    ):
        direction = "outgoing"
        related = target
    else:
        direction = "incoming"
        related = source

    return {
        "id": relationship.id,
        "project_id": relationship.project_id,
        "relationship_type": relationship.relationship_type,
        "relationship_label": perspective_label(
            relationship.relationship_type,
            direction,
        ),
        "direction": direction,
        "created_at": relationship.created_at,
        "source": source.response(),
        "target": target.response(),
        "related": related.response(),
    }


def create_entity_relationship(
    db: Session,
    project_id: int,
    user_id: int,
    payload: EntityRelationshipCreate,
) -> dict:
    if (
        payload.source_type == payload.target_type
        and payload.source_id == payload.target_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An entity cannot be related to itself",
        )

    _validate_relationship_rule(
        payload.source_type,
        payload.relationship_type,
        payload.target_type,
    )
    resolve_relationship_entity(
        db,
        project_id,
        payload.source_type,
        payload.source_id,
        require_selectable=True,
    )
    resolve_relationship_entity(
        db,
        project_id,
        payload.target_type,
        payload.target_id,
        require_selectable=True,
    )

    source_type, source_id, target_type, target_id = (
        canonicalize_relationship(
            payload.source_type,
            payload.source_id,
            payload.target_type,
            payload.target_id,
            payload.relationship_type,
        )
    )
    duplicate = (
        db.query(EntityRelationship.id)
        .filter(
            EntityRelationship.project_id == project_id,
            EntityRelationship.source_type == source_type,
            EntityRelationship.source_id == source_id,
            EntityRelationship.target_type == target_type,
            EntityRelationship.target_id == target_id,
            EntityRelationship.relationship_type
            == payload.relationship_type,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relationship already exists",
        )

    relationship = EntityRelationship(
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relationship_type=payload.relationship_type,
        created_by=user_id,
    )
    db.add(relationship)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relationship already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create relationship",
        ) from error

    db.refresh(relationship)
    summaries = resolve_entity_summaries(
        db,
        project_id,
        _relationship_references([relationship]),
    )
    return _serialize_relationship(
        relationship,
        summaries,
        payload.source_type,
        payload.source_id,
    )


def list_entity_relationships(
    db: Session,
    project_id: int,
    *,
    entity_type: str,
    entity_id: int,
    direction: str,
    relationship_type: str | None,
    related_type: str | None,
    limit: int,
    offset: int,
) -> dict:
    resolve_relationship_entity(db, project_id, entity_type, entity_id)
    if relationship_type is not None:
        _validate_relationship_type(relationship_type)

    source_match = and_(
        EntityRelationship.source_type == entity_type,
        EntityRelationship.source_id == entity_id,
    )
    target_match = and_(
        EntityRelationship.target_type == entity_type,
        EntityRelationship.target_id == entity_id,
    )
    symmetric_types = tuple(SYMMETRIC_RELATIONSHIP_TYPES)
    query = db.query(EntityRelationship).filter(
        EntityRelationship.project_id == project_id,
        EntityRelationship.deleted_at.is_(None),
    )

    if direction == "outgoing":
        query = query.filter(
            source_match,
            EntityRelationship.relationship_type.notin_(symmetric_types),
        )
    elif direction == "incoming":
        query = query.filter(
            target_match,
            EntityRelationship.relationship_type.notin_(symmetric_types),
        )
    elif direction == "symmetric":
        query = query.filter(
            or_(source_match, target_match),
            EntityRelationship.relationship_type.in_(symmetric_types),
        )
    else:
        query = query.filter(or_(source_match, target_match))

    if relationship_type is not None:
        query = query.filter(
            EntityRelationship.relationship_type == relationship_type
        )
    if related_type is not None:
        query = query.filter(
            or_(
                and_(
                    source_match,
                    EntityRelationship.target_type == related_type,
                ),
                and_(
                    target_match,
                    EntityRelationship.source_type == related_type,
                ),
            )
        )

    total = query.count()
    relationships = (
        query.order_by(
            EntityRelationship.created_at.desc(),
            EntityRelationship.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    summaries = resolve_entity_summaries(
        db,
        project_id,
        _relationship_references(relationships),
    )
    return {
        "relationships": [
            _serialize_relationship(
                relationship,
                summaries,
                entity_type,
                entity_id,
            )
            for relationship in relationships
        ],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(relationships) < total,
        },
    }


def _validate_relationship_type(relationship_type: str) -> None:
    if relationship_type not in RELATIONSHIP_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported relationship type",
        )


def delete_entity_relationship(
    db: Session,
    project_id: int,
    relationship_id: int,
) -> None:
    relationship = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.id == relationship_id,
            EntityRelationship.project_id == project_id,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )
    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        )

    deleted_at = utc_now()
    relationship.deleted_at = deleted_at
    relationship.updated_at = deleted_at
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete relationship",
        ) from error
