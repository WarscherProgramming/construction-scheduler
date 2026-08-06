from datetime import datetime, timezone

from sqlalchemy import (
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
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PreconstructionScopeAssertionSet(Base):
    """Immutable container for one successful structured extraction run."""

    __tablename__ = "preconstruction_scope_assertion_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'completed_with_warnings', 'failed_validation')",
            name="ck_preconstruction_scope_assertion_sets_status",
        ),
        CheckConstraint(
            "assertion_count >= 0 AND warning_count >= 0",
            name="ck_preconstruction_scope_assertion_sets_counts",
        ),
        CheckConstraint(
            "length(manifest_hash) = 64 AND length(content_hash) = 64",
            name="ck_preconstruction_scope_assertion_sets_hash_lengths",
        ),
        CheckConstraint(
            "length(trim(taxonomy_version)) > 0 AND length(trim(schema_version)) > 0",
            name="ck_preconstruction_scope_assertion_sets_versions_nonblank",
        ),
        UniqueConstraint(
            "analysis_run_id",
            name="uq_preconstruction_scope_assertion_sets_run",
        ),
        Index(
            "ix_preconstruction_scope_assertion_sets_review_listing",
            "project_id",
            "review_set_id",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    analysis_run_id = Column(
        Integer,
        ForeignKey("preconstruction_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    manifest_hash = Column(String(64), nullable=False)
    taxonomy_version = Column(String(100), nullable=False)
    schema_version = Column(String(100), nullable=False)
    provider_profile = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False)
    assertion_count = Column(Integer, nullable=False, default=0, server_default="0")
    warning_count = Column(Integer, nullable=False, default=0, server_default="0")
    warning_codes = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class PreconstructionScopeAssertion(Base):
    """One advisory scope statement. Provider-authored content is immutable.

    ``status`` is the server-controlled current review state. It is updated
    only inside the same transaction that appends a review row, so the
    append-only review history stays authoritative.
    """

    __tablename__ = "preconstruction_scope_assertions"
    __table_args__ = (
        CheckConstraint(
            "assertion_type IN ('requirement', 'physical_item', 'system', 'activity', "
            "'responsibility', 'deliverable', 'testing_requirement', "
            "'coordination_requirement', 'procurement_requirement', 'allowance', "
            "'alternate', 'exclusion', 'informational')",
            name="ck_preconstruction_scope_assertions_type",
        ),
        CheckConstraint(
            "inclusion_state IN ('included', 'excluded', 'conditional', "
            "'not_applicable', 'unspecified')",
            name="ck_preconstruction_scope_assertions_inclusion",
        ),
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'needs_review', 'superseded')",
            name="ck_preconstruction_scope_assertions_status",
        ),
        CheckConstraint(
            "origin IN ('provider', 'manual')",
            name="ck_preconstruction_scope_assertions_origin",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_preconstruction_scope_assertions_confidence",
        ),
        CheckConstraint(
            "length(trim(concept_code)) > 0 AND length(trim(taxonomy_version)) > 0",
            name="ck_preconstruction_scope_assertions_concept_nonblank",
        ),
        CheckConstraint(
            "length(trim(subject)) > 0",
            name="ck_preconstruction_scope_assertions_subject_nonblank",
        ),
        CheckConstraint(
            "quantity_value IS NULL OR quantity_value >= 0",
            name="ck_preconstruction_scope_assertions_quantity",
        ),
        CheckConstraint(
            "(quantity_unit IS NULL) OR (quantity_value IS NOT NULL)",
            name="ck_preconstruction_scope_assertions_unit_requires_value",
        ),
        # A provider assertion always belongs to an assertion set and carries a
        # provider key. A manual assertion carries neither, and never a
        # fabricated confidence.
        CheckConstraint(
            "(origin = 'provider' AND assertion_set_id IS NOT NULL "
            "AND provider_assertion_key IS NOT NULL) OR "
            "(origin = 'manual' AND assertion_set_id IS NULL "
            "AND provider_assertion_key IS NULL AND confidence IS NULL)",
            name="ck_preconstruction_scope_assertions_origin_consistency",
        ),
        CheckConstraint(
            "supersedes_assertion_id IS NULL OR supersedes_assertion_id <> id",
            name="ck_preconstruction_scope_assertions_not_self_superseding",
        ),
        UniqueConstraint(
            "assertion_set_id",
            "provider_assertion_key",
            name="uq_preconstruction_scope_assertions_set_provider_key",
        ),
        Index(
            "ix_preconstruction_scope_assertions_review_listing",
            "project_id",
            "review_set_id",
            "status",
            "id",
        ),
        Index(
            "ix_preconstruction_scope_assertions_set_order",
            "assertion_set_id",
            "id",
        ),
        Index(
            "ix_preconstruction_scope_assertions_source_concept",
            "project_id",
            "source_id",
            "concept_code",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    assertion_set_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertion_sets.id", ondelete="CASCADE"),
        nullable=True,
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    origin = Column(String(16), nullable=False, default="provider", server_default="provider")
    concept_code = Column(String(100), nullable=False)
    taxonomy_version = Column(String(100), nullable=False)
    assertion_type = Column(String(40), nullable=False)
    subject = Column(String(300), nullable=False)
    requirement_text = Column(String(2000), nullable=True)
    normalized_requirement = Column(Text, nullable=True)
    responsibility_party = Column(String(200), nullable=True)
    discipline = Column(String(120), nullable=True)
    trade = Column(String(120), nullable=True)
    specification_section = Column(String(60), nullable=True)
    drawing_sheet = Column(String(100), nullable=True)
    quantity_value = Column(Numeric(16, 4), nullable=True)
    quantity_unit = Column(String(40), nullable=True)
    location_text = Column(String(300), nullable=True)
    inclusion_state = Column(
        String(24), nullable=False, default="unspecified", server_default="unspecified"
    )
    confidence = Column(Numeric(4, 3), nullable=True)
    confidence_basis = Column(String(300), nullable=True)
    provider_assertion_key = Column(String(100), nullable=True)
    status = Column(
        String(24), nullable=False, default="proposed", server_default="proposed"
    )
    supersedes_assertion_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class PreconstructionAssertionEvidence(Base):
    """Immutable citation into an M18.2 content segment."""

    __tablename__ = "preconstruction_assertion_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_role IN ('primary', 'supporting', 'contextual', 'contradictory')",
            name="ck_preconstruction_assertion_evidence_role",
        ),
        CheckConstraint(
            "page_number >= 1",
            name="ck_preconstruction_assertion_evidence_page_number",
        ),
        CheckConstraint(
            "segment_index >= 0",
            name="ck_preconstruction_assertion_evidence_segment_index",
        ),
        CheckConstraint(
            "length(text_hash) = 64",
            name="ck_preconstruction_assertion_evidence_hash_length",
        ),
        CheckConstraint(
            "length(excerpt) >= 1 AND length(excerpt) <= 600",
            name="ck_preconstruction_assertion_evidence_excerpt_length",
        ),
        CheckConstraint(
            "(character_start IS NULL AND character_end IS NULL) OR "
            "(character_start >= 0 AND character_end >= character_start)",
            name="ck_preconstruction_assertion_evidence_offsets",
        ),
        UniqueConstraint(
            "assertion_id",
            "content_segment_id",
            "evidence_role",
            name="uq_preconstruction_assertion_evidence_segment_role",
        ),
        Index(
            "ix_preconstruction_assertion_evidence_assertion_order",
            "assertion_id",
            "page_number",
            "segment_index",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    assertion_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertions.id", ondelete="CASCADE"),
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
    character_start = Column(Integer, nullable=True)
    character_end = Column(Integer, nullable=True)
    evidence_role = Column(
        String(24), nullable=False, default="primary", server_default="primary"
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class PreconstructionAssertionReview(Base):
    """Append-only human review event. Rows are never updated or deleted."""

    __tablename__ = "preconstruction_assertion_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted', 'rejected', 'needs_review')",
            name="ck_preconstruction_assertion_reviews_decision",
        ),
        CheckConstraint(
            "reason_code IS NULL OR reason_code IN ("
            "'unsupported_by_evidence', 'incorrect_concept', "
            "'incorrect_scope_interpretation', 'duplicate', 'irrelevant', "
            "'intentional_exclusion', 'insufficient_detail', 'wrong_responsibility', "
            "'wrong_quantity', 'wrong_location', 'source_superseded', 'other')",
            name="ck_preconstruction_assertion_reviews_reason",
        ),
        CheckConstraint(
            "reviewer_note IS NULL OR length(reviewer_note) <= 2000",
            name="ck_preconstruction_assertion_reviews_note_length",
        ),
        CheckConstraint(
            "previous_review_id IS NULL OR previous_review_id <> id",
            name="ck_preconstruction_assertion_reviews_not_self_previous",
        ),
        Index(
            "ix_preconstruction_assertion_reviews_assertion_order",
            "assertion_id",
            "reviewed_at",
            "id",
        ),
        Index(
            "ix_preconstruction_assertion_reviews_project_listing",
            "project_id",
            "reviewed_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    assertion_id = Column(
        Integer,
        ForeignKey("preconstruction_scope_assertions.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision = Column(String(24), nullable=False)
    reason_code = Column(String(50), nullable=True)
    reviewer_note = Column(String(2000), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    previous_review_id = Column(
        Integer,
        ForeignKey("preconstruction_assertion_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )
