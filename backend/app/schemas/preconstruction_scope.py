"""Request and response contracts for scope assertions and human review.

Every mutation model forbids unknown fields. Clients never supply project
identity, origin, lifecycle status, confidence, provider keys, evidence
excerpts, content hashes, reviewer identity, or review timestamps; the server
computes all of them.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import MutationModel


AssertionTypeValue = Literal[
    "requirement",
    "physical_item",
    "system",
    "activity",
    "responsibility",
    "deliverable",
    "testing_requirement",
    "coordination_requirement",
    "procurement_requirement",
    "allowance",
    "alternate",
    "exclusion",
    "informational",
]
InclusionStateValue = Literal[
    "included", "excluded", "conditional", "not_applicable", "unspecified"
]
ReviewDecisionValue = Literal["accepted", "rejected", "needs_review"]
ReviewReasonValue = Literal[
    "unsupported_by_evidence",
    "incorrect_concept",
    "incorrect_scope_interpretation",
    "duplicate",
    "irrelevant",
    "intentional_exclusion",
    "insufficient_detail",
    "wrong_responsibility",
    "wrong_quantity",
    "wrong_location",
    "source_superseded",
    "other",
]
AssertionStatusValue = Literal[
    "proposed", "accepted", "rejected", "needs_review", "superseded"
]
AssertionOriginValue = Literal["provider", "manual"]


# --- taxonomy ---------------------------------------------------------------

class TaxonomyConceptResponse(MutationModel):
    code: str
    name: str
    category: str
    category_label: str
    scope_kind: str
    scope_kind_label: str
    description: str
    parent_code: str | None
    default_unit: str | None
    status: str
    deprecated_at: str | None
    aliases: list[str]


class LabeledValueResponse(MutationModel):
    value: str
    label: str


class ScopeTaxonomyResponse(MutationModel):
    taxonomy_version: str
    concepts: list[TaxonomyConceptResponse]
    categories: list[LabeledValueResponse]
    scope_kinds: list[LabeledValueResponse]
    assertion_types: list[LabeledValueResponse]
    inclusion_states: list[LabeledValueResponse]
    evidence_roles: list[LabeledValueResponse]
    review_reason_codes: list[LabeledValueResponse]
    total: int
    limit: int


# --- assertion sets ---------------------------------------------------------

class AssertionSetResponse(MutationModel):
    id: int
    project_id: int
    review_set_id: int
    analysis_run_id: int
    manifest_hash: str
    taxonomy_version: str
    schema_version: str
    provider_profile: str
    status: str
    assertion_count: int
    warning_count: int
    warnings: list[str]
    content_hash: str
    created_at: datetime
    completed_at: datetime | None


class AssertionSetListResponse(MutationModel):
    items: list[AssertionSetResponse]
    total: int
    limit: int
    offset: int
    latest_assertion_set_id: int | None


# --- assertions -------------------------------------------------------------

class AssertionEvidenceResponse(MutationModel):
    id: int
    source_id: int
    source_display_name: str | None
    document_role: str | None
    sheet_number: str | None
    revision_code: str | None
    snapshot_id: int
    page_number: int
    segment_index: int
    excerpt: str
    evidence_role: str
    evidence_role_label: str
    text_hash: str
    viewer_target: dict[str, Any]
    content_target: dict[str, Any]


class AssertionSourceResponse(MutationModel):
    id: int
    display_name: str
    document_role: str
    source_type: str
    document_id: int
    drawing_revision_id: int | None
    sheet_number: str | None
    revision_code: str | None
    discipline: str | None
    trade: str | None


class ScopeAssertionResponse(MutationModel):
    id: int
    assertion_set_id: int | None
    review_set_id: int
    origin: str
    origin_label: str
    concept_code: str
    concept_name: str
    concept_category: str | None
    concept_category_label: str | None
    concept_scope_kind: str | None
    concept_status: str
    taxonomy_version: str
    assertion_type: str
    assertion_type_label: str
    subject: str
    requirement_text: str | None
    responsibility_party: str | None
    discipline: str | None
    trade: str | None
    specification_section: str | None
    drawing_sheet: str | None
    quantity_value: float | None
    quantity_unit: str | None
    location_text: str | None
    inclusion_state: str
    inclusion_state_label: str
    confidence: float | None
    confidence_basis: str | None
    status: str
    status_label: str
    review_decision: str | None
    review_reason_code: str | None
    review_reason_label: str | None
    reviewer_note: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    supersedes_assertion_id: int | None
    created_at: datetime
    evidence_count: int
    evidence: list[AssertionEvidenceResponse]
    evidence_truncated: bool
    source: AssertionSourceResponse | None


class AssertionSummaryResponse(MutationModel):
    total: int
    proposed: int
    accepted: int
    rejected: int
    needs_review: int
    superseded: int
    manual: int


class ScopeAssertionListResponse(MutationModel):
    items: list[ScopeAssertionResponse]
    total: int
    limit: int
    offset: int
    summary: AssertionSummaryResponse
    latest_assertion_set_id: int | None
    taxonomy_version: str


class AssertionReviewResponse(MutationModel):
    id: int
    decision: str
    decision_label: str
    reason_code: str | None
    reason_label: str | None
    reviewer_note: str | None
    reviewed_by: int
    reviewed_at: datetime
    previous_review_id: int | None


class AssertionReviewListResponse(MutationModel):
    items: list[AssertionReviewResponse]


class ScopeAssertionDetailResponse(MutationModel):
    assertion: ScopeAssertionResponse
    reviews: list[AssertionReviewResponse]


# --- mutations --------------------------------------------------------------

class AssertionReviewCreate(MutationModel):
    """Human review decision. Reviewer identity is taken from the session."""

    decision: ReviewDecisionValue
    reason_code: ReviewReasonValue | None = None
    reviewer_note: str | None = Field(default=None, max_length=2000)


class ManualAssertionCreate(MutationModel):
    """Human-authored assertion.

    There is deliberately no field for confidence, origin, provider profile,
    status, evidence excerpts, or assertion-set membership.
    """

    source_id: int = Field(gt=0, le=2_147_483_647)
    concept_code: str = Field(min_length=1, max_length=100)
    assertion_type: AssertionTypeValue
    subject: str = Field(min_length=1, max_length=300)
    requirement_text: str | None = Field(default=None, max_length=2000)
    responsibility_party: str | None = Field(default=None, max_length=200)
    discipline: str | None = Field(default=None, max_length=120)
    trade: str | None = Field(default=None, max_length=120)
    specification_section: str | None = Field(default=None, max_length=60)
    drawing_sheet: str | None = Field(default=None, max_length=100)
    quantity_value: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    quantity_unit: str | None = Field(default=None, max_length=40)
    location_text: str | None = Field(default=None, max_length=300)
    inclusion_state: InclusionStateValue = "unspecified"
    evidence_segment_ids: list[int] = Field(min_length=1, max_length=20)
    reviewer_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_evidence_identifiers(self):
        for value in self.evidence_segment_ids:
            if value <= 0 or value > 2_147_483_647:
                raise ValueError("evidence_segment_ids must be positive identifiers")
        if len(set(self.evidence_segment_ids)) != len(self.evidence_segment_ids):
            raise ValueError("evidence_segment_ids must be unique")
        if self.quantity_unit is not None and self.quantity_value is None:
            raise ValueError("quantity_unit requires quantity_value")
        return self


class AssertionSupersedeRequest(MutationModel):
    replacement_assertion_id: int = Field(gt=0, le=2_147_483_647)
    reviewer_note: str = Field(min_length=1, max_length=2000)
