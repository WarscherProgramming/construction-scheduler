from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.preconstruction.roles import ANALYSIS_TYPES, DOCUMENT_ROLE_BY_VALUE, REVIEW_PURPOSES
from app.schemas.common import MutationModel, UpdateMutationModel


ReviewPurpose = Literal[
    "bid_scope_review",
    "subcontract_scope_review",
    "procurement_review",
    "submittal_coverage_review",
    "revision_impact_review",
    "general_scope_review",
]
DocumentRoleValue = Literal[
    "drawing",
    "specification",
    "addendum",
    "schedule",
    "equipment_schedule",
    "proposal",
    "subcontract",
    "purchase_order",
    "procurement_package",
    "submittal",
    "rfi",
    "change_order",
    "owner_directive",
    "other_reference",
]
AnalysisType = Literal["readiness_probe", "provider_contract_validation"]


class ReviewSetCreate(MutationModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    purpose: ReviewPurpose


class ReviewSetUpdate(UpdateMutationModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    purpose: ReviewPurpose | None = None


class ReviewSetResponse(MutationModel):
    id: int
    project_id: int
    name: str
    description: str | None
    purpose: str
    purpose_label: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ReviewSetListResponse(MutationModel):
    items: list[ReviewSetResponse]
    total: int
    limit: int
    offset: int


class ReviewSourceCreate(MutationModel):
    source_type: Literal["document", "drawing_revision"]
    document_id: int = Field(gt=0)
    drawing_revision_id: int | None = Field(default=None, gt=0)
    document_role: DocumentRoleValue
    discipline: str | None = Field(default=None, max_length=120)
    trade: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_typed_reference(self):
        if self.source_type == "document" and self.drawing_revision_id is not None:
            raise ValueError("drawing_revision_id is only valid for drawing revisions")
        if self.source_type == "drawing_revision" and self.drawing_revision_id is None:
            raise ValueError("drawing_revision_id is required for drawing revisions")
        return self


class ReviewSourceUpdate(UpdateMutationModel):
    document_role: DocumentRoleValue | None = None
    discipline: str | None = Field(default=None, max_length=120)
    trade: str | None = Field(default=None, max_length=120)


class ReviewSourceResponse(MutationModel):
    id: int
    project_id: int
    review_set_id: int
    source_type: str
    document_id: int
    drawing_revision_id: int | None
    document_role: str
    role_label: str
    role_category: str
    discipline: str | None
    trade: str | None
    source_checksum: str
    extraction_id: int | None
    extraction_version: str | None
    extraction_status: str
    display_name: str
    sheet_number: str | None
    revision_code: str | None
    route_target: dict[str, Any]
    added_by: int
    added_at: datetime
    locked: bool


class RoleOptionResponse(MutationModel):
    value: str
    label: str
    category: str


class ReviewSourceListResponse(MutationModel):
    items: list[ReviewSourceResponse]
    roles: list[RoleOptionResponse]


class ProviderCapabilityResponse(MutationModel):
    profile: str
    available: bool
    capability: str


class ReadinessResponse(MutationModel):
    ready: bool
    blockers: list[str]
    warnings: list[str]
    source_count: int
    requirement_source_count: int
    coverage_source_count: int
    context_source_count: int
    searchable_source_count: int
    unavailable_source_count: int
    manifest_preview_hash: str | None
    provider: ProviderCapabilityResponse


class AnalysisRunCreate(MutationModel):
    analysis_type: AnalysisType = "provider_contract_validation"


class AnalysisRunResponse(MutationModel):
    id: int
    review_set_id: int
    analysis_type: str
    analysis_type_label: str
    status: str
    provider_profile: str
    manifest_hash: str
    source_count: int
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    attempt_count: int
    max_attempts: int
    failure_code: str | None
    failure_message: str | None
    warnings: list[str]
    result_summary: dict[str, Any] | None
    can_cancel: bool
    can_retry: bool


class AnalysisRunListResponse(MutationModel):
    items: list[AnalysisRunResponse]
    total: int
    limit: int
    offset: int


class SourceCandidateResponse(MutationModel):
    source_type: str
    document_id: int
    drawing_revision_id: int | None
    display_name: str
    document_type: str
    extraction_status: str
    sheet_number: str | None
    revision_code: str | None
    is_current_revision: bool | None
    route_target: dict[str, Any]


class SourceCandidateListResponse(MutationModel):
    items: list[SourceCandidateResponse]
    limit: int


def purpose_label(value: str) -> str:
    return REVIEW_PURPOSES[value]


def role_metadata(value: str) -> tuple[str, str]:
    role = DOCUMENT_ROLE_BY_VALUE[value]
    return role.label, role.category


def analysis_type_label(value: str) -> str:
    return ANALYSIS_TYPES[value]
