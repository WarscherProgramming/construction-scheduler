"""Add immutable preconstruction content preparation.

Revision ID: b9e5d3f7a201
Revises: a8f4c2d6e190
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b9e5d3f7a201"
down_revision: str | Sequence[str] | None = "a8f4c2d6e190"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation', "
            "'content_contract_validation')",
        )

    op.create_table(
        "preconstruction_preparation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("lineage_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("extractor_version", sa.String(length=100), nullable=False),
        sa.Column("extraction_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renderer_version", sa.String(length=100), nullable=True),
        sa.Column("preparation_version", sa.String(length=100), nullable=False),
        sa.Column("segmentation_policy_version", sa.String(length=100), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("lease_token_digest", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.String(length=300), nullable=True),
        sa.Column("warning_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
            name="ck_preconstruction_preparation_runs_attempts",
        ),
        sa.CheckConstraint(
            "warning_count >= 0",
            name="ck_preconstruction_preparation_runs_warning_count",
        ),
        sa.CheckConstraint(
            "length(source_checksum) = 64 AND length(lineage_fingerprint) = 64",
            name="ck_preconstruction_preparation_runs_hash_lengths",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'completed_with_warnings', "
            "'failed', 'unavailable', 'cancelled')",
            name="ck_preconstruction_preparation_runs_status",
        ),
        sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["review_source_id"], ["preconstruction_review_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preconstruction_preparation_runs_id", "preconstruction_preparation_runs", ["id"])
    op.create_index(
        "uq_preconstruction_preparation_runs_active_lineage",
        "preconstruction_preparation_runs",
        ["review_source_id", "lineage_fingerprint"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'processing')"),
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.create_index(
        "ix_preconstruction_preparation_runs_pending",
        "preconstruction_preparation_runs",
        ["status", "available_at", "requested_at", "id"],
    )
    op.create_index(
        "ix_preconstruction_preparation_runs_lease",
        "preconstruction_preparation_runs",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_preconstruction_preparation_runs_source_listing",
        "preconstruction_preparation_runs",
        ["project_id", "review_source_id", "requested_at", "id"],
    )

    op.create_table(
        "preconstruction_content_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_source_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("drawing_revision_id", sa.Integer(), nullable=True),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("extractor_version", sa.String(length=100), nullable=False),
        sa.Column("extraction_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renderer_version", sa.String(length=100), nullable=True),
        sa.Column("preparation_version", sa.String(length=100), nullable=False),
        sa.Column("segmentation_policy_version", sa.String(length=100), nullable=False),
        sa.Column("lineage_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("segment_count", sa.Integer(), nullable=False),
        sa.Column("total_character_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("preparation_run_id", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_codes", sa.Text(), nullable=True),
        sa.Column("unavailable_reason", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "page_count >= 0 AND segment_count >= 0 AND total_character_count >= 0 AND warning_count >= 0",
            name="ck_preconstruction_content_snapshots_counts",
        ),
        sa.CheckConstraint(
            "length(source_checksum) = 64 AND length(lineage_fingerprint) = 64 AND length(content_hash) = 64",
            name="ck_preconstruction_content_snapshots_hash_lengths",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'completed_with_warnings', "
            "'unavailable', 'failed', 'cancelled')",
            name="ck_preconstruction_content_snapshots_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drawing_revision_id"], ["drawing_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["preparation_run_id"], ["preconstruction_preparation_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_source_id"], ["preconstruction_review_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preparation_run_id", name="uq_preconstruction_content_snapshots_preparation_run"),
        sa.UniqueConstraint("review_source_id", "lineage_fingerprint", name="uq_preconstruction_content_snapshots_source_lineage"),
    )
    op.create_index("ix_preconstruction_content_snapshots_id", "preconstruction_content_snapshots", ["id"])
    op.create_index(
        "ix_preconstruction_content_snapshots_source_status",
        "preconstruction_content_snapshots",
        ["project_id", "review_source_id", "status", "created_at", "id"],
    )
    op.create_index(
        "ix_preconstruction_content_snapshots_project_document",
        "preconstruction_content_snapshots",
        ["project_id", "document_id", "id"],
    )

    op.create_table(
        "preconstruction_content_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("page_label", sa.String(length=100), nullable=True),
        sa.Column("sheet_number", sa.String(length=100), nullable=True),
        sa.Column("width_points", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("height_points", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("rotation", sa.Integer(), nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_text_hash", sa.String(length=64), nullable=False),
        sa.Column("has_searchable_text", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("has_visual_content", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("warning_codes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("character_count >= 0", name="ck_preconstruction_content_pages_character_count"),
        sa.CheckConstraint("height_points IS NULL OR height_points > 0", name="ck_preconstruction_content_pages_height"),
        sa.CheckConstraint("length(page_text_hash) = 64", name="ck_preconstruction_content_pages_hash_length"),
        sa.CheckConstraint("page_number >= 1", name="ck_preconstruction_content_pages_number"),
        sa.CheckConstraint("rotation IS NULL OR rotation IN (0, 90, 180, 270)", name="ck_preconstruction_content_pages_rotation"),
        sa.CheckConstraint("width_points IS NULL OR width_points > 0", name="ck_preconstruction_content_pages_width"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["preconstruction_content_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "page_number", name="uq_preconstruction_content_pages_snapshot_page"),
    )
    op.create_index("ix_preconstruction_content_pages_id", "preconstruction_content_pages", ["id"])
    op.create_index(
        "ix_preconstruction_content_pages_snapshot_order",
        "preconstruction_content_pages",
        ["snapshot_id", "page_number", "id"],
    )

    op.create_table(
        "preconstruction_content_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("segment_type", sa.String(length=24), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("character_start", sa.Integer(), nullable=True),
        sa.Column("character_end", sa.Integer(), nullable=True),
        sa.Column("token_estimate", sa.Integer(), nullable=True),
        sa.Column("heading_path", sa.String(length=500), nullable=True),
        sa.Column("bounding_box", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 100)", name="ck_preconstruction_content_segments_confidence"),
        sa.CheckConstraint("length(text_hash) = 64", name="ck_preconstruction_content_segments_hash_length"),
        sa.CheckConstraint("segment_index >= 0", name="ck_preconstruction_content_segments_index"),
        sa.CheckConstraint("(character_start IS NULL AND character_end IS NULL) OR (character_start >= 0 AND character_end >= character_start)", name="ck_preconstruction_content_segments_offsets"),
        sa.CheckConstraint("length(text) >= 1 AND length(text) <= 8000", name="ck_preconstruction_content_segments_text_length"),
        sa.CheckConstraint("token_estimate IS NULL OR token_estimate >= 0", name="ck_preconstruction_content_segments_tokens"),
        sa.CheckConstraint("segment_type IN ('page_text', 'paragraph', 'heading', 'metadata')", name="ck_preconstruction_content_segments_type"),
        sa.ForeignKeyConstraint(["page_id"], ["preconstruction_content_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["preconstruction_content_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "segment_index", name="uq_preconstruction_content_segments_page_index"),
    )
    op.create_index("ix_preconstruction_content_segments_id", "preconstruction_content_segments", ["id"])
    op.create_index(
        "ix_preconstruction_content_segments_snapshot_order",
        "preconstruction_content_segments",
        ["snapshot_id", "page_id", "segment_index", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_preconstruction_content_segments_snapshot_order", table_name="preconstruction_content_segments")
    op.drop_index("ix_preconstruction_content_segments_id", table_name="preconstruction_content_segments")
    op.drop_table("preconstruction_content_segments")
    op.drop_index("ix_preconstruction_content_pages_snapshot_order", table_name="preconstruction_content_pages")
    op.drop_index("ix_preconstruction_content_pages_id", table_name="preconstruction_content_pages")
    op.drop_table("preconstruction_content_pages")
    op.drop_index("ix_preconstruction_content_snapshots_project_document", table_name="preconstruction_content_snapshots")
    op.drop_index("ix_preconstruction_content_snapshots_source_status", table_name="preconstruction_content_snapshots")
    op.drop_index("ix_preconstruction_content_snapshots_id", table_name="preconstruction_content_snapshots")
    op.drop_table("preconstruction_content_snapshots")
    op.drop_index("ix_preconstruction_preparation_runs_source_listing", table_name="preconstruction_preparation_runs")
    op.drop_index("ix_preconstruction_preparation_runs_lease", table_name="preconstruction_preparation_runs")
    op.drop_index("ix_preconstruction_preparation_runs_pending", table_name="preconstruction_preparation_runs")
    op.drop_index("uq_preconstruction_preparation_runs_active_lineage", table_name="preconstruction_preparation_runs")
    op.drop_index("ix_preconstruction_preparation_runs_id", table_name="preconstruction_preparation_runs")
    op.drop_table("preconstruction_preparation_runs")
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation')",
        )
