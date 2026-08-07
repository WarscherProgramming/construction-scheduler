from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


_COMPARISON_TYPE_SQL = (
    "comparison_type IN ('requirement_vs_proposal', 'requirement_vs_subcontract', "
    "'requirement_vs_purchase_order', 'requirement_vs_procurement_package', "
    "'requirement_vs_submittal', 'specification_vs_drawing', "
    "'drawing_vs_drawing_revision', 'proposal_vs_subcontract', "
    "'contract_vs_proposal', 'requirement_vs_change_order', "
    "'equipment_schedule_vs_purchase_order', 'general_scope_coverage')"
)
_FINDING_TYPE_SQL = (
    "finding_type IN ('missing_coverage', 'partial_coverage', 'conflicting_scope', "
    "'explicit_exclusion', 'conditional_scope', 'responsibility_conflict', "
    "'quantity_mismatch', 'location_mismatch', 'revision_added_scope', "
    "'revision_removed_scope', 'revision_changed_scope', 'duplicate_scope', "
    "'unsupported_assertion', 'informational_difference')"
)
_SEVERITY_SQL = (
    "severity IN ('informational', 'low', 'medium', 'high', 'critical')"
)
_MATCH_CLASS_SQL = (
    "deterministic_match_class IN ('exact', 'strong', 'partial', 'weak', 'none')"
)


class PreconstructionComparisonPlan(Base):
    """A named, deterministic definition of what is being compared.

    Editable while ``draft``; the first comparison run locks it so historical
    runs stay reproducible. Archived plans are read-only. There is no hard
    delete.
    """

    __tablename__ = "preconstruction_comparison_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready', 'locked', 'archived')",
            name="ck_preconstruction_comparison_plans_status",
        ),
        CheckConstraint(
            _COMPARISON_TYPE_SQL,
            name="ck_preconstruction_comparison_plans_type",
        ),
        CheckConstraint(
            "minimum_review_state IN ('accepted', 'accepted_or_needs_review')",
            name="ck_preconstruction_comparison_plans_review_state",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_preconstruction_comparison_plans_name_nonblank",
        ),
        CheckConstraint(
            "length(configuration_hash) = 64",
            name="ck_preconstruction_comparison_plans_hash_length",
        ),
        UniqueConstraint(
            "review_set_id",
            "normalized_name",
            name="uq_preconstruction_comparison_plans_review_set_name",
        ),
        Index(
            "ix_preconstruction_comparison_plans_listing",
            "project_id",
            "review_set_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    description = Column(String(2000), nullable=True)
    comparison_type = Column(String(60), nullable=False)
    status = Column(String(16), nullable=False, default="draft", server_default="draft")
    taxonomy_version = Column(String(100), nullable=False)
    # Controlled JSON: role allowlists and assertion-set id lists only. No
    # arbitrary filter expressions are ever accepted or stored.
    left_role_filters = Column(Text, nullable=True)
    right_role_filters = Column(Text, nullable=True)
    left_assertion_set_ids = Column(Text, nullable=True)
    right_assertion_set_ids = Column(Text, nullable=True)
    include_manual_assertions = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    minimum_review_state = Column(
        String(32), nullable=False, default="accepted", server_default="accepted"
    )
    configuration_json = Column(Text, nullable=False)
    configuration_hash = Column(String(64), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        onupdate=utc_now, server_default=func.now()
    )
    locked_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)


class PreconstructionFindingSet(Base):
    """Immutable result of one comparison execution."""

    __tablename__ = "preconstruction_finding_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'completed_with_warnings', 'failed_validation')",
            name="ck_preconstruction_finding_sets_status",
        ),
        CheckConstraint(
            _COMPARISON_TYPE_SQL,
            name="ck_preconstruction_finding_sets_type",
        ),
        CheckConstraint(
            "finding_count >= 0 AND warning_count >= 0 AND candidate_count >= 0",
            name="ck_preconstruction_finding_sets_counts",
        ),
        CheckConstraint(
            "length(comparison_manifest_hash) = 64 AND length(content_hash) = 64",
            name="ck_preconstruction_finding_sets_hash_lengths",
        ),
        UniqueConstraint(
            "analysis_run_id",
            name="uq_preconstruction_finding_sets_analysis_run",
        ),
        Index(
            "ix_preconstruction_finding_sets_plan_listing",
            "project_id",
            "comparison_plan_id",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    comparison_plan_id = Column(
        Integer,
        ForeignKey("preconstruction_comparison_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Null for a deterministic-only execution that never queued provider work.
    analysis_run_id = Column(
        Integer,
        ForeignKey("preconstruction_analysis_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    comparison_type = Column(String(60), nullable=False)
    comparison_manifest_hash = Column(String(64), nullable=False)
    taxonomy_version = Column(String(100), nullable=False)
    schema_version = Column(String(100), nullable=False)
    provider_profile = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False)
    candidate_count = Column(Integer, nullable=False, default=0, server_default="0")
    finding_count = Column(Integer, nullable=False, default=0, server_default="0")
    warning_count = Column(Integer, nullable=False, default=0, server_default="0")
    warning_codes = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class PreconstructionFinding(Base):
    """One advisory comparison statement.

    ``status`` is the server-controlled current review state, updated only in
    the same transaction that appends a review row.
    """

    __tablename__ = "preconstruction_findings"
    __table_args__ = (
        CheckConstraint(_FINDING_TYPE_SQL, name="ck_preconstruction_findings_type"),
        CheckConstraint(_SEVERITY_SQL, name="ck_preconstruction_findings_severity"),
        CheckConstraint(
            "origin IN ('deterministic', 'provider_validated', 'manual')",
            name="ck_preconstruction_findings_origin",
        ),
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'needs_review', "
            "'intentional_exclusion', 'superseded')",
            name="ck_preconstruction_findings_status",
        ),
        CheckConstraint(_MATCH_CLASS_SQL, name="ck_preconstruction_findings_match_class"),
        CheckConstraint(
            "deterministic_match_score IS NULL OR "
            "(deterministic_match_score >= 0 AND deterministic_match_score <= 100)",
            name="ck_preconstruction_findings_match_score",
        ),
        CheckConstraint(
            "provider_confidence IS NULL OR "
            "(provider_confidence >= 0 AND provider_confidence <= 1)",
            name="ck_preconstruction_findings_provider_confidence",
        ),
        CheckConstraint(
            "length(trim(title)) > 0 AND length(trim(finding_key)) > 0",
            name="ck_preconstruction_findings_text_nonblank",
        ),
        # A manual finding is human-authored and never carries provider
        # confidence; a provider-validated finding always belongs to a set.
        CheckConstraint(
            "(origin = 'manual' AND provider_confidence IS NULL) OR origin <> 'manual'",
            name="ck_preconstruction_findings_manual_has_no_confidence",
        ),
        CheckConstraint(
            "supersedes_finding_id IS NULL OR supersedes_finding_id <> id",
            name="ck_preconstruction_findings_not_self_superseding",
        ),
        UniqueConstraint(
            "finding_set_id",
            "finding_key",
            name="uq_preconstruction_findings_set_key",
        ),
        Index(
            "ix_preconstruction_findings_plan_listing",
            "project_id",
            "comparison_plan_id",
            "status",
            "severity",
            "id",
        ),
        Index(
            "ix_preconstruction_findings_set_order",
            "finding_set_id",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    finding_set_id = Column(
        Integer,
        ForeignKey("preconstruction_finding_sets.id", ondelete="CASCADE"),
        nullable=True,
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    comparison_plan_id = Column(
        Integer,
        ForeignKey("preconstruction_comparison_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_key = Column(String(200), nullable=False)
    finding_type = Column(String(40), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(String(600), nullable=True)
    rationale = Column(String(2000), nullable=True)
    origin = Column(
        String(24), nullable=False, default="deterministic", server_default="deterministic"
    )
    deterministic_match_class = Column(
        String(16), nullable=False, default="none", server_default="none"
    )
    deterministic_match_score = Column(Integer, nullable=True)
    match_reasons = Column(Text, nullable=True)
    provider_disposition = Column(String(24), nullable=True)
    provider_confidence = Column(Numeric(4, 3), nullable=True)
    provider_confidence_basis = Column(String(300), nullable=True)
    status = Column(
        String(32), nullable=False, default="proposed", server_default="proposed"
    )
    supersedes_finding_id = Column(
        Integer,
        ForeignKey("preconstruction_findings.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class PreconstructionFindingAssertion(Base):
    """Link between a finding and one M18.3 assertion, with its match context."""

    __tablename__ = "preconstruction_finding_assertions"
    __table_args__ = (
        CheckConstraint(
            "side IN ('requirement', 'coverage', 'context', 'prior_revision', "
            "'current_revision')",
            name="ck_preconstruction_finding_assertions_side",
        ),
        CheckConstraint(
            "link_role IN ('primary', 'supporting', 'contradictory', 'near_match')",
            name="ck_preconstruction_finding_assertions_role",
        ),
        CheckConstraint(
            "match_class IN ('exact', 'strong', 'partial', 'weak', 'none')",
            name="ck_preconstruction_finding_assertions_match_class",
        ),
        UniqueConstraint(
            "finding_id",
            "assertion_id",
            "side",
            name="uq_preconstruction_finding_assertions_finding_assertion_side",
        ),
        Index(
            "ix_preconstruction_finding_assertions_finding_order",
            "finding_id",
            "side",
            "assertion_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    finding_id = Column(
        Integer,
        ForeignKey("preconstruction_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The exact review decision that made this assertion eligible, pinned so a
    # later review change cannot rewrite a historical finding.
    assertion_review_id = Column(
        Integer,
        ForeignKey("preconstruction_assertion_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )
    side = Column(String(24), nullable=False)
    link_role = Column(String(24), nullable=False, default="primary", server_default="primary")
    match_class = Column(String(16), nullable=False, default="none", server_default="none")
    match_reasons = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class PreconstructionFindingEvidence(Base):
    """Immutable citation carried forward from M18.3 assertion evidence."""

    __tablename__ = "preconstruction_finding_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_role IN ('primary', 'supporting', 'contextual', 'contradictory')",
            name="ck_preconstruction_finding_evidence_role",
        ),
        CheckConstraint(
            "page_number >= 1 AND segment_index >= 0",
            name="ck_preconstruction_finding_evidence_coordinates",
        ),
        CheckConstraint(
            "length(text_hash) = 64",
            name="ck_preconstruction_finding_evidence_hash_length",
        ),
        CheckConstraint(
            "length(excerpt) >= 1 AND length(excerpt) <= 600",
            name="ck_preconstruction_finding_evidence_excerpt_length",
        ),
        UniqueConstraint(
            "finding_id",
            "assertion_evidence_id",
            "evidence_role",
            name="uq_preconstruction_finding_evidence_source_role",
        ),
        Index(
            "ix_preconstruction_finding_evidence_finding_order",
            "finding_id",
            "page_number",
            "segment_index",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    finding_id = Column(
        Integer,
        ForeignKey("preconstruction_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assertion_evidence_id = Column(
        Integer,
        ForeignKey("preconstruction_assertion_evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_snapshot_id = Column(
        Integer,
        ForeignKey("preconstruction_content_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_page_id = Column(
        Integer,
        ForeignKey("preconstruction_content_pages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_segment_id = Column(
        Integer,
        ForeignKey("preconstruction_content_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=False)
    segment_index = Column(Integer, nullable=False)
    text_hash = Column(String(64), nullable=False)
    excerpt = Column(String(600), nullable=False)
    evidence_role = Column(
        String(24), nullable=False, default="primary", server_default="primary"
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class PreconstructionFindingReview(Base):
    """Append-only human decision on one finding. Never updated or deleted."""

    __tablename__ = "preconstruction_finding_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted', 'rejected', 'needs_review', "
            "'intentional_exclusion')",
            name="ck_preconstruction_finding_reviews_decision",
        ),
        CheckConstraint(
            "reason_code IS NULL OR reason_code IN ('confirmed_gap', "
            "'confirmed_conflict', 'intentional_exclusion', 'covered_elsewhere', "
            "'duplicate', 'incorrect_match', 'insufficient_evidence', "
            "'wrong_comparison_type', 'superseded_source', 'not_applicable', "
            "'requires_trade_review', 'requires_legal_review', 'other')",
            name="ck_preconstruction_finding_reviews_reason",
        ),
        CheckConstraint(
            "reviewer_note IS NULL OR length(reviewer_note) <= 2000",
            name="ck_preconstruction_finding_reviews_note_length",
        ),
        CheckConstraint(
            "previous_review_id IS NULL OR previous_review_id <> id",
            name="ck_preconstruction_finding_reviews_not_self_previous",
        ),
        Index(
            "ix_preconstruction_finding_reviews_finding_order",
            "finding_id",
            "reviewed_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    finding_id = Column(
        Integer,
        ForeignKey("preconstruction_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision = Column(String(32), nullable=False)
    reason_code = Column(String(50), nullable=True)
    reviewer_note = Column(String(2000), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    previous_review_id = Column(
        Integer,
        ForeignKey("preconstruction_finding_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )
