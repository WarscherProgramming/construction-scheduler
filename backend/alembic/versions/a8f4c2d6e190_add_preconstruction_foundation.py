"""Add provider-neutral preconstruction review foundation.

Revision ID: a8f4c2d6e190
Revises: f7c5d0b3e826
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a8f4c2d6e190"
down_revision: str | Sequence[str] | None = "f7c5d0b3e826"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "preconstruction_review_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_preconstruction_review_sets_name_nonblank"),
        sa.CheckConstraint(
            "purpose IN ('bid_scope_review', 'subcontract_scope_review', 'procurement_review', "
            "'submittal_coverage_review', 'revision_impact_review', 'general_scope_review')",
            name="ck_preconstruction_review_sets_purpose",
        ),
        sa.CheckConstraint("status IN ('draft', 'ready', 'archived')", name="ck_preconstruction_review_sets_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "normalized_name", name="uq_preconstruction_review_sets_project_name"),
    )
    op.create_index("ix_preconstruction_review_sets_id", "preconstruction_review_sets", ["id"])
    op.create_index(
        "ix_preconstruction_review_sets_project_listing",
        "preconstruction_review_sets",
        ["project_id", "status", "created_at", "id"],
    )

    op.create_table(
        "preconstruction_review_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("drawing_revision_id", sa.Integer(), nullable=True),
        sa.Column("document_role", sa.String(length=32), nullable=False),
        sa.Column("discipline", sa.String(length=120), nullable=True),
        sa.Column("trade", sa.String(length=120), nullable=True),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=True),
        sa.Column("extraction_version", sa.String(length=100), nullable=True),
        sa.Column("extraction_status", sa.String(length=32), nullable=False),
        sa.Column("display_name_snapshot", sa.String(length=500), nullable=False),
        sa.Column("sheet_number_snapshot", sa.String(length=100), nullable=True),
        sa.Column("revision_code_snapshot", sa.String(length=50), nullable=True),
        sa.Column("added_by", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "document_role IN ('drawing', 'specification', 'addendum', 'schedule', "
            "'equipment_schedule', 'proposal', 'subcontract', 'purchase_order', "
            "'procurement_package', 'submittal', 'rfi', 'change_order', "
            "'owner_directive', 'other_reference')",
            name="ck_preconstruction_review_sources_role",
        ),
        sa.CheckConstraint("source_type IN ('document', 'drawing_revision')", name="ck_preconstruction_review_sources_type"),
        sa.CheckConstraint(
            "(source_type = 'document' AND drawing_revision_id IS NULL) OR "
            "(source_type = 'drawing_revision' AND drawing_revision_id IS NOT NULL)",
            name="ck_preconstruction_review_sources_typed_reference",
        ),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drawing_revision_id"], ["drawing_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preconstruction_review_sources_id", "preconstruction_review_sources", ["id"])
    op.create_index(
        "ix_preconstruction_review_sources_project_document",
        "preconstruction_review_sources",
        ["project_id", "document_id", "id"],
    )
    op.create_index(
        "ix_preconstruction_review_sources_set_listing",
        "preconstruction_review_sources",
        ["review_set_id", "removed_at", "added_at", "id"],
    )
    op.create_index(
        "uq_preconstruction_review_sources_active_logical",
        "preconstruction_review_sources",
        ["review_set_id", "source_type", "document_id"],
        unique=True,
        sqlite_where=sa.text("removed_at IS NULL"),
        postgresql_where=sa.text("removed_at IS NULL"),
    )

    op.create_table(
        "preconstruction_analysis_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("provider_profile", sa.String(length=50), nullable=False),
        sa.Column("analysis_type", sa.String(length=50), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_attempt_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.String(length=300), nullable=True),
        sa.Column("result_summary_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("analysis_type IN ('readiness_probe', 'provider_contract_validation')", name="ck_preconstruction_analysis_runs_type"),
        sa.CheckConstraint("current_attempt_count >= 1 AND max_attempts >= current_attempt_count", name="ck_preconstruction_analysis_runs_attempts"),
        sa.CheckConstraint("source_count >= 1", name="ck_preconstruction_analysis_runs_source_count"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled', 'unavailable')",
            name="ck_preconstruction_analysis_runs_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preconstruction_analysis_runs_id", "preconstruction_analysis_runs", ["id"])
    op.create_index(
        "ix_preconstruction_analysis_runs_project_status",
        "preconstruction_analysis_runs",
        ["project_id", "status", "updated_at", "id"],
    )
    op.create_index(
        "ix_preconstruction_analysis_runs_set_listing",
        "preconstruction_analysis_runs",
        ["review_set_id", "requested_at", "id"],
    )
    op.create_index(
        "uq_preconstruction_analysis_runs_active_manifest",
        "preconstruction_analysis_runs",
        ["review_set_id", "manifest_hash", "provider_profile", "analysis_type"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'processing')"),
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )

    op.create_table(
        "preconstruction_analysis_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider_profile", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("lease_token", sa.String(length=64), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.String(length=300), nullable=True),
        sa.Column("input_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("output_schema_version", sa.String(length=100), nullable=False),
        sa.Column("provider_request_id", sa.String(length=120), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_units", sa.Integer(), nullable=True),
        sa.Column("output_units", sa.Integer(), nullable=True),
        sa.Column("safe_result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("attempt_number >= 1", name="ck_preconstruction_analysis_attempts_number"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_preconstruction_analysis_attempts_latency"),
        sa.CheckConstraint("input_units IS NULL OR input_units >= 0", name="ck_preconstruction_analysis_attempts_input_units"),
        sa.CheckConstraint("output_units IS NULL OR output_units >= 0", name="ck_preconstruction_analysis_attempts_output_units"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')", name="ck_preconstruction_analysis_attempts_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["preconstruction_analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "attempt_number", name="uq_preconstruction_analysis_attempts_run_number"),
    )
    op.create_index("ix_preconstruction_analysis_attempts_id", "preconstruction_analysis_attempts", ["id"])
    op.create_index(
        "ix_preconstruction_analysis_attempts_lease",
        "preconstruction_analysis_attempts",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_preconstruction_analysis_attempts_pending",
        "preconstruction_analysis_attempts",
        ["status", "available_at", "created_at", "id"],
    )
    op.create_index(
        "ix_preconstruction_analysis_attempts_project_run",
        "preconstruction_analysis_attempts",
        ["project_id", "run_id", "attempt_number"],
    )
    op.create_index(
        "uq_preconstruction_analysis_attempts_active_run",
        "preconstruction_analysis_attempts",
        ["run_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'processing')"),
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )


def downgrade() -> None:
    op.drop_index("uq_preconstruction_analysis_attempts_active_run", table_name="preconstruction_analysis_attempts")
    op.drop_index("ix_preconstruction_analysis_attempts_project_run", table_name="preconstruction_analysis_attempts")
    op.drop_index("ix_preconstruction_analysis_attempts_pending", table_name="preconstruction_analysis_attempts")
    op.drop_index("ix_preconstruction_analysis_attempts_lease", table_name="preconstruction_analysis_attempts")
    op.drop_index("ix_preconstruction_analysis_attempts_id", table_name="preconstruction_analysis_attempts")
    op.drop_table("preconstruction_analysis_attempts")
    op.drop_index("uq_preconstruction_analysis_runs_active_manifest", table_name="preconstruction_analysis_runs")
    op.drop_index("ix_preconstruction_analysis_runs_set_listing", table_name="preconstruction_analysis_runs")
    op.drop_index("ix_preconstruction_analysis_runs_project_status", table_name="preconstruction_analysis_runs")
    op.drop_index("ix_preconstruction_analysis_runs_id", table_name="preconstruction_analysis_runs")
    op.drop_table("preconstruction_analysis_runs")
    op.drop_index("uq_preconstruction_review_sources_active_logical", table_name="preconstruction_review_sources")
    op.drop_index("ix_preconstruction_review_sources_set_listing", table_name="preconstruction_review_sources")
    op.drop_index("ix_preconstruction_review_sources_project_document", table_name="preconstruction_review_sources")
    op.drop_index("ix_preconstruction_review_sources_id", table_name="preconstruction_review_sources")
    op.drop_table("preconstruction_review_sources")
    op.drop_index("ix_preconstruction_review_sets_project_listing", table_name="preconstruction_review_sets")
    op.drop_index("ix_preconstruction_review_sets_id", table_name="preconstruction_review_sets")
    op.drop_table("preconstruction_review_sets")
