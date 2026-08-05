from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PreconstructionReviewSet(Base):
    __tablename__ = "preconstruction_review_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready', 'archived')",
            name="ck_preconstruction_review_sets_status",
        ),
        CheckConstraint(
            "purpose IN ('bid_scope_review', 'subcontract_scope_review', "
            "'procurement_review', 'submittal_coverage_review', "
            "'revision_impact_review', 'general_scope_review')",
            name="ck_preconstruction_review_sets_purpose",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_preconstruction_review_sets_name_nonblank",
        ),
        UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_preconstruction_review_sets_project_name",
        ),
        Index(
            "ix_preconstruction_review_sets_project_listing",
            "project_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    description = Column(String(2000), nullable=True)
    purpose = Column(String(40), nullable=False)
    status = Column(String(16), nullable=False, default="draft", server_default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        onupdate=utc_now, server_default=func.now()
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)


class PreconstructionReviewSource(Base):
    __tablename__ = "preconstruction_review_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('document', 'drawing_revision')",
            name="ck_preconstruction_review_sources_type",
        ),
        CheckConstraint(
            "document_role IN ('drawing', 'specification', 'addendum', "
            "'schedule', 'equipment_schedule', 'proposal', 'subcontract', "
            "'purchase_order', 'procurement_package', 'submittal', 'rfi', "
            "'change_order', 'owner_directive', 'other_reference')",
            name="ck_preconstruction_review_sources_role",
        ),
        CheckConstraint(
            "(source_type = 'document' AND drawing_revision_id IS NULL) OR "
            "(source_type = 'drawing_revision' AND drawing_revision_id IS NOT NULL)",
            name="ck_preconstruction_review_sources_typed_reference",
        ),
        Index(
            "uq_preconstruction_review_sources_active_logical",
            "review_set_id",
            "source_type",
            "document_id",
            unique=True,
            sqlite_where=text("removed_at IS NULL"),
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index(
            "ix_preconstruction_review_sources_set_listing",
            "review_set_id",
            "removed_at",
            "added_at",
            "id",
        ),
        Index(
            "ix_preconstruction_review_sources_project_document",
            "project_id",
            "document_id",
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
    source_type = Column(String(24), nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    drawing_revision_id = Column(
        Integer, ForeignKey("drawing_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    document_role = Column(String(32), nullable=False)
    discipline = Column(String(120), nullable=True)
    trade = Column(String(120), nullable=True)
    source_checksum = Column(String(64), nullable=False)
    extraction_id = Column(
        Integer, ForeignKey("document_extractions.id", ondelete="SET NULL"), nullable=True
    )
    extraction_version = Column(String(100), nullable=True)
    extraction_status = Column(String(32), nullable=False)
    display_name_snapshot = Column(String(500), nullable=False)
    sheet_number_snapshot = Column(String(100), nullable=True)
    revision_code_snapshot = Column(String(50), nullable=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    locked_at = Column(DateTime(timezone=True), nullable=True)
    removed_at = Column(DateTime(timezone=True), nullable=True)


class PreconstructionAnalysisRun(Base):
    __tablename__ = "preconstruction_analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', "
            "'completed_with_warnings', 'failed', 'cancelled', 'unavailable')",
            name="ck_preconstruction_analysis_runs_status",
        ),
        CheckConstraint(
            "analysis_type IN ('readiness_probe', 'provider_contract_validation')",
            name="ck_preconstruction_analysis_runs_type",
        ),
        CheckConstraint(
            "source_count >= 1",
            name="ck_preconstruction_analysis_runs_source_count",
        ),
        CheckConstraint(
            "current_attempt_count >= 1 AND max_attempts >= current_attempt_count",
            name="ck_preconstruction_analysis_runs_attempts",
        ),
        Index(
            "uq_preconstruction_analysis_runs_active_manifest",
            "review_set_id",
            "manifest_hash",
            "provider_profile",
            "analysis_type",
            unique=True,
            sqlite_where=text("status IN ('pending', 'processing')"),
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        Index(
            "ix_preconstruction_analysis_runs_set_listing",
            "review_set_id",
            "requested_at",
            "id",
        ),
        Index(
            "ix_preconstruction_analysis_runs_project_status",
            "project_id",
            "status",
            "updated_at",
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
    status = Column(String(32), nullable=False, default="pending", server_default="pending")
    provider_profile = Column(String(50), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    manifest_hash = Column(String(64), nullable=False)
    manifest_json = Column(Text, nullable=False)
    source_count = Column(Integer, nullable=False)
    template_version = Column(String(100), nullable=False)
    schema_version = Column(String(100), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    current_attempt_count = Column(Integer, nullable=False, default=1, server_default="1")
    max_attempts = Column(Integer, nullable=False)
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(String(300), nullable=True)
    result_summary_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        onupdate=utc_now, server_default=func.now()
    )


class PreconstructionAnalysisAttempt(Base):
    __tablename__ = "preconstruction_analysis_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_preconstruction_analysis_attempts_status",
        ),
        CheckConstraint(
            "attempt_number >= 1",
            name="ck_preconstruction_analysis_attempts_number",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_preconstruction_analysis_attempts_latency",
        ),
        CheckConstraint(
            "input_units IS NULL OR input_units >= 0",
            name="ck_preconstruction_analysis_attempts_input_units",
        ),
        CheckConstraint(
            "output_units IS NULL OR output_units >= 0",
            name="ck_preconstruction_analysis_attempts_output_units",
        ),
        UniqueConstraint(
            "run_id", "attempt_number", name="uq_preconstruction_analysis_attempts_run_number"
        ),
        Index(
            "uq_preconstruction_analysis_attempts_active_run",
            "run_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'processing')"),
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        Index(
            "ix_preconstruction_analysis_attempts_pending",
            "status",
            "available_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_preconstruction_analysis_attempts_lease",
            "status",
            "lease_expires_at",
        ),
        Index(
            "ix_preconstruction_analysis_attempts_project_run",
            "project_id",
            "run_id",
            "attempt_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    run_id = Column(
        Integer,
        ForeignKey("preconstruction_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False)
    provider_profile = Column(String(50), nullable=False)
    provider_name = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    lease_token = Column(String(64), nullable=True)
    available_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(String(300), nullable=True)
    input_manifest_hash = Column(String(64), nullable=False)
    output_schema_version = Column(String(100), nullable=False)
    provider_request_id = Column(String(120), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    input_units = Column(Integer, nullable=True)
    output_units = Column(Integer, nullable=True)
    safe_result_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        onupdate=utc_now, server_default=func.now()
    )
