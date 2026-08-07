"""Request and response contracts for scope comparison and findings.

Every mutation model forbids unknown fields. Clients never supply project
identity, manifest or content hashes, lifecycle status, origin, provider
profile or confidence, match scores or reasons, evidence excerpts, reviewer
identity, or review timestamps; the server computes all of them.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import MutationModel, UpdateMutationModel


ComparisonTypeValue = Literal[
    "requirement_vs_proposal",
    "requirement_vs_subcontract",
    "requirement_vs_purchase_order",
    "requirement_vs_procurement_package",
    "requirement_vs_submittal",
    "specification_vs_drawing",
    "drawing_vs_drawing_revision",
    "proposal_vs_subcontract",
    "contract_vs_proposal",
    "requirement_vs_change_order",
    "equipment_schedule_vs_purchase_order",
    "general_scope_coverage",
]
FindingTypeValue = Literal[
    "missing_coverage",
    "partial_coverage",
    "conflicting_scope",
    "explicit_exclusion",
    "conditional_scope",
    "responsibility_conflict",
    "quantity_mismatch",
    "location_mismatch",
    "revision_added_scope",
    "revision_removed_scope",
    "revision_changed_scope",
    "duplicate_scope",
    "unsupported_assertion",
    "informational_difference",
]
SeverityValue = Literal["informational", "low", "medium", "high", "critical"]
FindingStatusValue = Literal[
    "proposed", "accepted", "rejected", "needs_review",
    "intentional_exclusion", "superseded",
]
FindingOriginValue = Literal["deterministic", "provider_validated", "manual"]
FindingSideValue = Literal[
    "requirement", "coverage", "context", "prior_revision", "current_revision"
]
FindingLinkRoleValue = Literal["primary", "supporting", "contradictory", "near_match"]
ReviewDecisionValue = Literal[
    "accepted", "rejected", "needs_review", "intentional_exclusion"
]
ReviewReasonValue = Literal[
    "confirmed_gap",
    "confirmed_conflict",
    "intentional_exclusion",
    "covered_elsewhere",
    "duplicate",
    "incorrect_match",
    "insufficient_evidence",
    "wrong_comparison_type",
    "superseded_source",
    "not_applicable",
    "requires_trade_review",
    "requires_legal_review",
    "other",
]
MinimumReviewStateValue = Literal["accepted", "accepted_or_needs_review"]


# --- comparison plans -------------------------------------------------------

class ComparisonPlanCreate(MutationModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    comparison_type: ComparisonTypeValue
    left_role_filters: list[str] | None = Field(default=None, max_length=20)
    right_role_filters: list[str] | None = Field(default=None, max_length=20)
    left_assertion_set_ids: list[int] | None = Field(default=None, max_length=50)
    right_assertion_set_ids: list[int] | None = Field(default=None, max_length=50)
    include_manual_assertions: bool = True
    minimum_review_state: MinimumReviewStateValue = "accepted"

    @model_validator(mode="after")
    def validate_identifiers(self):
        for group in (self.left_assertion_set_ids, self.right_assertion_set_ids):
            for value in group or []:
                if value <= 0 or value > 2_147_483_647:
                    raise ValueError("assertion set ids must be positive identifiers")
        for group in (self.left_role_filters, self.right_role_filters):
            for value in group or []:
                if not value or len(value) > 40:
                    raise ValueError("role filters must be short controlled values")
        return self


class ComparisonPlanUpdate(UpdateMutationModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    comparison_type: ComparisonTypeValue | None = None
    left_role_filters: list[str] | None = Field(default=None, max_length=20)
    right_role_filters: list[str] | None = Field(default=None, max_length=20)
    left_assertion_set_ids: list[int] | None = Field(default=None, max_length=50)
    right_assertion_set_ids: list[int] | None = Field(default=None, max_length=50)
    include_manual_assertions: bool | None = None
    minimum_review_state: MinimumReviewStateValue | None = None


class ComparisonPlanResponse(MutationModel):
    id: int
    project_id: int
    review_set_id: int
    name: str
    description: str | None
    comparison_type: str
    comparison_type_label: str
    comparison_type_description: str | None
    revision_lineage: bool
    status: str
    status_label: str
    taxonomy_version: str
    left_role_filters: list[str]
    right_role_filters: list[str]
    left_assertion_set_ids: list[int]
    right_assertion_set_ids: list[int]
    include_manual_assertions: bool
    minimum_review_state: str
    configuration_hash: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    locked_at: datetime | None
    archived_at: datetime | None
    editable: bool


class ComparisonTypeResponse(MutationModel):
    value: str
    label: str
    description: str
    left_roles: list[str]
    right_roles: list[str]
    allowed_finding_types: list[str]
    provider_validation_eligible: bool
    revision_lineage: bool
    notes: str


class ComparisonPlanListResponse(MutationModel):
    items: list[ComparisonPlanResponse]
    total: int
    limit: int
    offset: int
    comparison_types: list[ComparisonTypeResponse]


class ComparisonReadinessResponse(MutationModel):
    ready: bool
    blockers: list[str]
    warnings: list[str]
    comparison_type: str
    requirement_assertion_count: int
    coverage_assertion_count: int
    accepted_assertion_count: int
    stale_assertion_count: int
    unsupported_taxonomy_count: int
    deterministic_comparison_available: bool
    provider_validation_available: bool
    provider_profile: str
    taxonomy_version: str


class ComparisonRunRequest(MutationModel):
    """Deterministic comparison by default; provider validation is opt-in."""

    provider_validation: bool = False


# --- finding sets and findings ---------------------------------------------

class FindingSetResponse(MutationModel):
    id: int
    project_id: int
    review_set_id: int
    comparison_plan_id: int
    analysis_run_id: int | None
    comparison_type: str
    comparison_manifest_hash: str
    taxonomy_version: str
    schema_version: str
    provider_profile: str
    status: str
    candidate_count: int
    finding_count: int
    warning_count: int
    warnings: list[Any]
    content_hash: str
    created_at: datetime
    completed_at: datetime | None


class FindingSetListResponse(MutationModel):
    items: list[FindingSetResponse]
    total: int
    limit: int
    offset: int
    latest_finding_set_id: int | None


class MatchReasonResponse(MutationModel):
    code: str
    label: str


class FindingAssertionResponse(MutationModel):
    assertion_id: int
    side: str
    side_label: str
    link_role: str
    link_role_label: str
    match_class: str
    match_class_label: str
    match_reasons: list[MatchReasonResponse]
    subject: str | None
    concept_code: str | None
    concept_name: str | None
    concept_category_label: str | None
    inclusion_state: str | None
    responsibility_party: str | None
    quantity_value: float | None
    quantity_unit: str | None
    location_text: str | None
    source_id: int | None
    source_display_name: str | None
    document_role: str | None
    sheet_number: str | None
    revision_code: str | None


class FindingEvidenceResponse(MutationModel):
    id: int
    assertion_id: int
    source_id: int
    source_display_name: str | None
    snapshot_id: int
    page_number: int
    segment_index: int
    excerpt: str
    evidence_role: str
    text_hash: str
    content_target: dict[str, Any]


class FindingResponse(MutationModel):
    id: int
    finding_set_id: int | None
    comparison_plan_id: int
    review_set_id: int
    finding_type: str
    finding_type_label: str
    severity: str
    severity_label: str
    title: str
    summary: str | None
    rationale: str | None
    origin: str
    origin_label: str
    deterministic_match_class: str
    deterministic_match_class_label: str
    deterministic_match_score: int | None
    match_reasons: list[MatchReasonResponse]
    provider_disposition: str | None
    provider_confidence: float | None
    provider_confidence_basis: str | None
    status: str
    status_label: str
    review_decision: str | None
    review_reason_code: str | None
    review_reason_label: str | None
    reviewer_note: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    supersedes_finding_id: int | None
    created_at: datetime
    assertions: list[FindingAssertionResponse]
    evidence_count: int
    evidence: list[FindingEvidenceResponse]
    evidence_truncated: bool


class FindingSummaryResponse(MutationModel):
    total: int
    proposed: int
    accepted: int
    rejected: int
    needs_review: int
    intentional_exclusion: int
    superseded: int
    missing_coverage: int
    partial_coverage: int
    conflicts: int
    exclusions: int
    revision_impacts: int
    manual: int


class FindingListResponse(MutationModel):
    items: list[FindingResponse]
    total: int
    limit: int
    offset: int
    summary: FindingSummaryResponse
    latest_finding_set_id: int | None
    taxonomy_version: str


class FindingReviewResponse(MutationModel):
    id: int
    decision: str
    decision_label: str
    reason_code: str | None
    reason_label: str | None
    reviewer_note: str | None
    reviewed_by: int
    reviewed_at: datetime
    previous_review_id: int | None


class FindingDetailResponse(MutationModel):
    finding: FindingResponse
    reviews: list[FindingReviewResponse]


# --- mutations --------------------------------------------------------------

class FindingReviewCreate(MutationModel):
    decision: ReviewDecisionValue
    reason_code: ReviewReasonValue | None = None
    reviewer_note: str | None = Field(default=None, max_length=2000)


class ManualFindingAssertionLink(MutationModel):
    assertion_id: int = Field(gt=0, le=2_147_483_647)
    side: FindingSideValue
    link_role: FindingLinkRoleValue = "primary"


class ManualFindingCreate(MutationModel):
    """Human-authored finding.

    There is deliberately no field for origin, provider confidence, provider
    disposition, match score or reasons, lifecycle status, or evidence
    excerpts.
    """

    finding_type: FindingTypeValue
    severity: SeverityValue | None = None
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=600)
    rationale: str | None = Field(default=None, max_length=2000)
    assertions: list[ManualFindingAssertionLink] = Field(min_length=1, max_length=20)
    evidence_ids: list[int] = Field(default_factory=list, max_length=20)
    reviewer_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_links(self):
        seen = {(item.assertion_id, item.side) for item in self.assertions}
        if len(seen) != len(self.assertions):
            raise ValueError("assertion links must be unique per assertion and side")
        for value in self.evidence_ids:
            if value <= 0 or value > 2_147_483_647:
                raise ValueError("evidence ids must be positive identifiers")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence ids must be unique")
        return self


class FindingSupersedeRequest(MutationModel):
    replacement_finding_id: int = Field(gt=0, le=2_147_483_647)
    reviewer_note: str = Field(min_length=1, max_length=2000)
