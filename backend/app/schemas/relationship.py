from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import MutationModel


EntityType = Literal[
    "document",
    "drawing_set",
    "drawing_sheet",
    "drawing_revision",
    "drawing_issue",
    "rfi",
    "submittal",
    "punch_item",
    "change_order",
    "daily_log",
]
RelationshipType = Literal[
    "references",
    "responds_to",
    "supersedes",
    "supports",
    "impacts",
    "originated_from",
    "resolves",
    "documents",
    "includes",
    "associated_with",
    "located_on",
    "generated_by",
]
RelationshipDirection = Literal["outgoing", "incoming", "symmetric"]
RelationshipDirectionFilter = Literal[
    "both",
    "outgoing",
    "incoming",
    "symmetric",
]
RelationshipRoutePage = Literal[
    "projectDocuments",
    "projectDrawings",
    "drawingViewer",
    "rfis",
    "submittals",
    "punchItems",
    "changeOrders",
    "dailyLogs",
]
PositiveId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class EntityRelationshipCreate(MutationModel):
    source_type: EntityType
    source_id: PositiveId
    target_type: EntityType
    target_id: PositiveId
    relationship_type: RelationshipType

    @model_validator(mode="after")
    def reject_self_relationship(self):
        if (
            self.source_type == self.target_type
            and self.source_id == self.target_id
        ):
            raise ValueError("An entity cannot be related to itself")
        return self


class RelationshipRouteResponse(BaseModel):
    page: RelationshipRoutePage
    sheet_id: int | None = None
    revision_id: int | None = None


class RelationshipEntityResponse(BaseModel):
    type: EntityType
    id: int
    identifier: str
    title: str
    status: str | None
    route: RelationshipRouteResponse | None
    available: bool


class EntityRelationshipResponse(BaseModel):
    id: int
    project_id: int
    relationship_type: RelationshipType
    relationship_label: str
    direction: RelationshipDirection
    created_at: datetime
    source: RelationshipEntityResponse
    target: RelationshipEntityResponse
    related: RelationshipEntityResponse


class RelationshipPaginationResponse(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class EntityRelationshipListResponse(BaseModel):
    relationships: list[EntityRelationshipResponse]
    pagination: RelationshipPaginationResponse


class RelationshipCandidateListResponse(BaseModel):
    candidates: list[RelationshipEntityResponse]
    has_more: bool
