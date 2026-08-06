"""Add construction scope assertions and human review.

Revision ID: c1f7b4e28d35
Revises: b9e5d3f7a201
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c1f7b4e28d35"
down_revision: str | Sequence[str] | None = "b9e5d3f7a201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation', "
            "'content_contract_validation', 'scope_assertion_extraction')",
        )

    op.create_table(
        "preconstruction_scope_assertion_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("provider_profile", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assertion_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_codes", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "assertion_count >= 0 AND warning_count >= 0",
            name="ck_preconstruction_scope_assertion_sets_counts",
        ),
        sa.CheckConstraint(
            "length(manifest_hash) = 64 AND length(content_hash) = 64",
            name="ck_preconstruction_scope_assertion_sets_hash_lengths",
        ),
        sa.CheckConstraint(
            "length(trim(taxonomy_version)) > 0 AND length(trim(schema_version)) > 0",
            name="ck_preconstruction_scope_assertion_sets_versions_nonblank",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'completed_with_warnings', 'failed_validation')",
            name="ck_preconstruction_scope_assertion_sets_status",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["preconstruction_analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", name="uq_preconstruction_scope_assertion_sets_run"),
    )
    op.create_index(
        "ix_preconstruction_scope_assertion_sets_id",
        "preconstruction_scope_assertion_sets",
        ["id"],
    )
    op.create_index(
        "ix_preconstruction_scope_assertion_sets_review_listing",
        "preconstruction_scope_assertion_sets",
        ["project_id", "review_set_id", "created_at", "id"],
    )

    op.create_table(
        "preconstruction_scope_assertions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assertion_set_id", sa.Integer(), nullable=True),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=16), server_default=sa.text("'provider'"), nullable=False),
        sa.Column("concept_code", sa.String(length=100), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=100), nullable=False),
        sa.Column("assertion_type", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("requirement_text", sa.String(length=2000), nullable=True),
        sa.Column("normalized_requirement", sa.Text(), nullable=True),
        sa.Column("responsibility_party", sa.String(length=200), nullable=True),
        sa.Column("discipline", sa.String(length=120), nullable=True),
        sa.Column("trade", sa.String(length=120), nullable=True),
        sa.Column("specification_section", sa.String(length=60), nullable=True),
        sa.Column("drawing_sheet", sa.String(length=100), nullable=True),
        sa.Column("quantity_value", sa.Numeric(precision=16, scale=4), nullable=True),
        sa.Column("quantity_unit", sa.String(length=40), nullable=True),
        sa.Column("location_text", sa.String(length=300), nullable=True),
        sa.Column("inclusion_state", sa.String(length=24), server_default=sa.text("'unspecified'"), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("confidence_basis", sa.String(length=300), nullable=True),
        sa.Column("provider_assertion_key", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'proposed'"), nullable=False),
        sa.Column("supersedes_assertion_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(origin = 'provider' AND assertion_set_id IS NOT NULL "
            "AND provider_assertion_key IS NOT NULL) OR "
            "(origin = 'manual' AND assertion_set_id IS NULL "
            "AND provider_assertion_key IS NULL AND confidence IS NULL)",
            name="ck_preconstruction_scope_assertions_origin_consistency",
        ),
        sa.CheckConstraint(
            "(quantity_unit IS NULL) OR (quantity_value IS NOT NULL)",
            name="ck_preconstruction_scope_assertions_unit_requires_value",
        ),
        sa.CheckConstraint(
            "assertion_type IN ('requirement', 'physical_item', 'system', 'activity', "
            "'responsibility', 'deliverable', 'testing_requirement', "
            "'coordination_requirement', 'procurement_requirement', 'allowance', "
            "'alternate', 'exclusion', 'informational')",
            name="ck_preconstruction_scope_assertions_type",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_preconstruction_scope_assertions_confidence",
        ),
        sa.CheckConstraint(
            "inclusion_state IN ('included', 'excluded', 'conditional', "
            "'not_applicable', 'unspecified')",
            name="ck_preconstruction_scope_assertions_inclusion",
        ),
        sa.CheckConstraint(
            "length(trim(concept_code)) > 0 AND length(trim(taxonomy_version)) > 0",
            name="ck_preconstruction_scope_assertions_concept_nonblank",
        ),
        sa.CheckConstraint(
            "length(trim(subject)) > 0",
            name="ck_preconstruction_scope_assertions_subject_nonblank",
        ),
        sa.CheckConstraint(
            "origin IN ('provider', 'manual')",
            name="ck_preconstruction_scope_assertions_origin",
        ),
        sa.CheckConstraint(
            "quantity_value IS NULL OR quantity_value >= 0",
            name="ck_preconstruction_scope_assertions_quantity",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'needs_review', 'superseded')",
            name="ck_preconstruction_scope_assertions_status",
        ),
        sa.CheckConstraint(
            "supersedes_assertion_id IS NULL OR supersedes_assertion_id <> id",
            name="ck_preconstruction_scope_assertions_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(["assertion_set_id"], ["preconstruction_scope_assertion_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["preconstruction_review_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_assertion_id"], ["preconstruction_scope_assertions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assertion_set_id",
            "provider_assertion_key",
            name="uq_preconstruction_scope_assertions_set_provider_key",
        ),
    )
    op.create_index("ix_preconstruction_scope_assertions_id", "preconstruction_scope_assertions", ["id"])
    op.create_index(
        "ix_preconstruction_scope_assertions_review_listing",
        "preconstruction_scope_assertions",
        ["project_id", "review_set_id", "status", "id"],
    )
    op.create_index(
        "ix_preconstruction_scope_assertions_set_order",
        "preconstruction_scope_assertions",
        ["assertion_set_id", "id"],
    )
    op.create_index(
        "ix_preconstruction_scope_assertions_source_concept",
        "preconstruction_scope_assertions",
        ["project_id", "source_id", "concept_code"],
    )

    op.create_table(
        "preconstruction_assertion_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assertion_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("content_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("content_page_id", sa.Integer(), nullable=False),
        sa.Column("content_segment_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("excerpt", sa.String(length=600), nullable=False),
        sa.Column("character_start", sa.Integer(), nullable=True),
        sa.Column("character_end", sa.Integer(), nullable=True),
        sa.Column("evidence_role", sa.String(length=24), server_default=sa.text("'primary'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(character_start IS NULL AND character_end IS NULL) OR "
            "(character_start >= 0 AND character_end >= character_start)",
            name="ck_preconstruction_assertion_evidence_offsets",
        ),
        sa.CheckConstraint(
            "evidence_role IN ('primary', 'supporting', 'contextual', 'contradictory')",
            name="ck_preconstruction_assertion_evidence_role",
        ),
        sa.CheckConstraint(
            "length(excerpt) >= 1 AND length(excerpt) <= 600",
            name="ck_preconstruction_assertion_evidence_excerpt_length",
        ),
        sa.CheckConstraint(
            "length(text_hash) = 64",
            name="ck_preconstruction_assertion_evidence_hash_length",
        ),
        sa.CheckConstraint("page_number >= 1", name="ck_preconstruction_assertion_evidence_page_number"),
        sa.CheckConstraint("segment_index >= 0", name="ck_preconstruction_assertion_evidence_segment_index"),
        sa.ForeignKeyConstraint(["assertion_id"], ["preconstruction_scope_assertions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_page_id"], ["preconstruction_content_pages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["content_segment_id"], ["preconstruction_content_segments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["content_snapshot_id"], ["preconstruction_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["preconstruction_review_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assertion_id",
            "content_segment_id",
            "evidence_role",
            name="uq_preconstruction_assertion_evidence_segment_role",
        ),
    )
    op.create_index("ix_preconstruction_assertion_evidence_id", "preconstruction_assertion_evidence", ["id"])
    op.create_index(
        "ix_preconstruction_assertion_evidence_assertion_order",
        "preconstruction_assertion_evidence",
        ["assertion_id", "page_number", "segment_index", "id"],
    )

    op.create_table(
        "preconstruction_assertion_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assertion_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("reviewer_note", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("previous_review_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('accepted', 'rejected', 'needs_review')",
            name="ck_preconstruction_assertion_reviews_decision",
        ),
        sa.CheckConstraint(
            "previous_review_id IS NULL OR previous_review_id <> id",
            name="ck_preconstruction_assertion_reviews_not_self_previous",
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN ("
            "'unsupported_by_evidence', 'incorrect_concept', "
            "'incorrect_scope_interpretation', 'duplicate', 'irrelevant', "
            "'intentional_exclusion', 'insufficient_detail', 'wrong_responsibility', "
            "'wrong_quantity', 'wrong_location', 'source_superseded', 'other')",
            name="ck_preconstruction_assertion_reviews_reason",
        ),
        sa.CheckConstraint(
            "reviewer_note IS NULL OR length(reviewer_note) <= 2000",
            name="ck_preconstruction_assertion_reviews_note_length",
        ),
        sa.ForeignKeyConstraint(["assertion_id"], ["preconstruction_scope_assertions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["previous_review_id"], ["preconstruction_assertion_reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preconstruction_assertion_reviews_id", "preconstruction_assertion_reviews", ["id"])
    op.create_index(
        "ix_preconstruction_assertion_reviews_assertion_order",
        "preconstruction_assertion_reviews",
        ["assertion_id", "reviewed_at", "id"],
    )
    op.create_index(
        "ix_preconstruction_assertion_reviews_project_listing",
        "preconstruction_assertion_reviews",
        ["project_id", "reviewed_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_preconstruction_assertion_reviews_project_listing", table_name="preconstruction_assertion_reviews")
    op.drop_index("ix_preconstruction_assertion_reviews_assertion_order", table_name="preconstruction_assertion_reviews")
    op.drop_index("ix_preconstruction_assertion_reviews_id", table_name="preconstruction_assertion_reviews")
    op.drop_table("preconstruction_assertion_reviews")
    op.drop_index("ix_preconstruction_assertion_evidence_assertion_order", table_name="preconstruction_assertion_evidence")
    op.drop_index("ix_preconstruction_assertion_evidence_id", table_name="preconstruction_assertion_evidence")
    op.drop_table("preconstruction_assertion_evidence")
    op.drop_index("ix_preconstruction_scope_assertions_source_concept", table_name="preconstruction_scope_assertions")
    op.drop_index("ix_preconstruction_scope_assertions_set_order", table_name="preconstruction_scope_assertions")
    op.drop_index("ix_preconstruction_scope_assertions_review_listing", table_name="preconstruction_scope_assertions")
    op.drop_index("ix_preconstruction_scope_assertions_id", table_name="preconstruction_scope_assertions")
    op.drop_table("preconstruction_scope_assertions")
    op.drop_index("ix_preconstruction_scope_assertion_sets_review_listing", table_name="preconstruction_scope_assertion_sets")
    op.drop_index("ix_preconstruction_scope_assertion_sets_id", table_name="preconstruction_scope_assertion_sets")
    op.drop_table("preconstruction_scope_assertion_sets")
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation', "
            "'content_contract_validation')",
        )
