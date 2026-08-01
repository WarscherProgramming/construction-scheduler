from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.relationship import (
    EntityRelationshipCreate,
    EntityRelationshipListResponse,
    EntityRelationshipResponse,
    EntityType,
    RelationshipCandidateListResponse,
    RelationshipDirectionFilter,
    RelationshipType,
)
from app.services.relationship import (
    create_entity_relationship,
    delete_entity_relationship,
    list_entity_relationships,
)
from app.services.relationship_resolver import (
    get_entity_resolver,
    search_relationship_candidates,
)


router = APIRouter()


@router.get(
    "/projects/{project_id}/relationships",
    response_model=EntityRelationshipListResponse,
)
def get_project_relationships(
    project_id: int,
    response: Response,
    entity_type: EntityType,
    entity_id: Annotated[int, Query(ge=1, le=2_147_483_647)],
    direction: RelationshipDirectionFilter = "both",
    relationship_type: RelationshipType | None = None,
    related_type: EntityType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return list_entity_relationships(
        db,
        project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        direction=direction,
        relationship_type=relationship_type,
        related_type=related_type,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/relationships",
    response_model=EntityRelationshipResponse,
    status_code=201,
)
def post_project_relationship(
    project_id: int,
    payload: EntityRelationshipCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return create_entity_relationship(
        db,
        project_id,
        current_user["id"],
        payload,
    )


@router.delete(
    "/projects/{project_id}/relationships/{relationship_id}",
    response_model=MessageResponse,
)
def delete_project_relationship(
    project_id: int,
    relationship_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    delete_entity_relationship(db, project_id, relationship_id)
    return {"message": "Relationship deleted"}


@router.get(
    "/projects/{project_id}/relationship-candidates",
    response_model=RelationshipCandidateListResponse,
)
def get_project_relationship_candidates(
    project_id: int,
    response: Response,
    entity_type: EntityType,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    exclude_type: EntityType | None = None,
    exclude_id: Annotated[
        int | None,
        Query(ge=1, le=2_147_483_647),
    ] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    get_entity_resolver(entity_type)
    if (exclude_type is None) != (exclude_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="exclude_type and exclude_id must be provided together",
        )
    effective_exclude_id = (
        exclude_id if exclude_type == entity_type else None
    )
    candidates, has_more = search_relationship_candidates(
        db,
        project_id,
        entity_type,
        search=search,
        limit=limit,
        exclude_id=effective_exclude_id,
    )
    response.headers["Cache-Control"] = "no-store"
    return {
        "candidates": [candidate.response() for candidate in candidates],
        "has_more": has_more,
    }
