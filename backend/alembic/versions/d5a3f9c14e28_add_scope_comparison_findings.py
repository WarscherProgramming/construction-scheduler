"""Add cross-document scope comparison and evidence-backed findings.

Revision ID: d5a3f9c14e28
Revises: c1f7b4e28d35
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d5a3f9c14e28"
down_revision: str | Sequence[str] | None = "c1f7b4e28d35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COMPARISON_TYPE_SQL = (
    "comparison_type IN ('requirement_vs_proposal', 'requirement_vs_subcontract', "
    "'requirement_vs_purchase_order', 'requirement_vs_procurement_package', "
    "'requirement_vs_submittal', 'specification_vs_drawing', "
    "'drawing_vs_drawing_revision', 'proposal_vs_subcontract', "
    "'contract_vs_proposal', 'requirement_vs_change_order', "
    "'equipment_schedule_vs_purchase_order', 'general_scope_coverage')"
)
FINDING_TYPE_SQL = (
    "finding_type IN ('missing_coverage', 'partial_coverage', 'conflicting_scope', "
    "'explicit_exclusion', 'conditional_scope', 'responsibility_conflict', "
    "'quantity_mismatch', 'location_mismatch', 'revision_added_scope', "
    "'revision_removed_scope', 'revision_changed_scope', 'duplicate_scope', "
    "'unsupported_assertion', 'informational_difference')"
)


def upgrade() -> None:
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation', "
            "'content_contract_validation', 'scope_assertion_extraction', "
            "'scope_comparison', 'scope_comparison_validation')",
        )

    op.create_table(
        "preconstruction_comparison_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("comparison_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=100), nullable=False),
        sa.Column("left_role_filters", sa.Text(), nullable=True),
        sa.Column("right_role_filters", sa.Text(), nullable=True),
        sa.Column("left_assertion_set_ids", sa.Text(), nullable=True),
        sa.Column("right_assertion_set_ids", sa.Text(), nullable=True),
        sa.Column("include_manual_assertions", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("minimum_review_state", sa.String(length=32), server_default=sa.text("'accepted'"), nullable=False),
        sa.Column("configuration_json", sa.Text(), nullable=False),
        sa.Column("configuration_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(COMPARISON_TYPE_SQL, name="ck_preconstruction_comparison_plans_type"),
        sa.CheckConstraint("length(configuration_hash) = 64", name="ck_preconstruction_comparison_plans_hash_length"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_preconstruction_comparison_plans_name_nonblank"),
        sa.CheckConstraint(
            "minimum_review_state IN ('accepted', 'accepted_or_needs_review')",
            name="ck_preconstruction_comparison_plans_review_state",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'locked', 'archived')",
            name="ck_preconstruction_comparison_plans_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_set_id", "normalized_name", name="uq_preconstruction_comparison_plans_review_set_name"),
    )
    op.create_index("ix_preconstruction_comparison_plans_id", "preconstruction_comparison_plans", ["id"])
    op.create_index(
        "ix_preconstruction_comparison_plans_listing",
        "preconstruction_comparison_plans",
        ["project_id", "review_set_id", "status", "created_at", "id"],
    )

    op.create_table(
        "preconstruction_finding_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("comparison_plan_id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), nullable=True),
        sa.Column("comparison_type", sa.String(length=60), nullable=False),
        sa.Column("comparison_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("provider_profile", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("finding_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_codes", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(COMPARISON_TYPE_SQL, name="ck_preconstruction_finding_sets_type"),
        sa.CheckConstraint(
            "finding_count >= 0 AND warning_count >= 0 AND candidate_count >= 0",
            name="ck_preconstruction_finding_sets_counts",
        ),
        sa.CheckConstraint(
            "length(comparison_manifest_hash) = 64 AND length(content_hash) = 64",
            name="ck_preconstruction_finding_sets_hash_lengths",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'completed_with_warnings', 'failed_validation')",
            name="ck_preconstruction_finding_sets_status",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["preconstruction_analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comparison_plan_id"], ["preconstruction_comparison_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", name="uq_preconstruction_finding_sets_analysis_run"),
    )
    op.create_index("ix_preconstruction_finding_sets_id", "preconstruction_finding_sets", ["id"])
    op.create_index(
        "ix_preconstruction_finding_sets_plan_listing",
        "preconstruction_finding_sets",
        ["project_id", "comparison_plan_id", "created_at", "id"],
    )

    op.create_table(
        "preconstruction_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("finding_set_id", sa.Integer(), nullable=True),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("comparison_plan_id", sa.Integer(), nullable=False),
        sa.Column("finding_key", sa.String(length=200), nullable=False),
        sa.Column("finding_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=600), nullable=True),
        sa.Column("rationale", sa.String(length=2000), nullable=True),
        sa.Column("origin", sa.String(length=24), server_default=sa.text("'deterministic'"), nullable=False),
        sa.Column("deterministic_match_class", sa.String(length=16), server_default=sa.text("'none'"), nullable=False),
        sa.Column("deterministic_match_score", sa.Integer(), nullable=True),
        sa.Column("match_reasons", sa.Text(), nullable=True),
        sa.Column("provider_disposition", sa.String(length=24), nullable=True),
        sa.Column("provider_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("provider_confidence_basis", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'proposed'"), nullable=False),
        sa.Column("supersedes_finding_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(FINDING_TYPE_SQL, name="ck_preconstruction_findings_type"),
        sa.CheckConstraint(
            "(origin = 'manual' AND provider_confidence IS NULL) OR origin <> 'manual'",
            name="ck_preconstruction_findings_manual_has_no_confidence",
        ),
        sa.CheckConstraint(
            "deterministic_match_class IN ('exact', 'strong', 'partial', 'weak', 'none')",
            name="ck_preconstruction_findings_match_class",
        ),
        sa.CheckConstraint(
            "deterministic_match_score IS NULL OR "
            "(deterministic_match_score >= 0 AND deterministic_match_score <= 100)",
            name="ck_preconstruction_findings_match_score",
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0 AND length(trim(finding_key)) > 0",
            name="ck_preconstruction_findings_text_nonblank",
        ),
        sa.CheckConstraint(
            "origin IN ('deterministic', 'provider_validated', 'manual')",
            name="ck_preconstruction_findings_origin",
        ),
        sa.CheckConstraint(
            "provider_confidence IS NULL OR "
            "(provider_confidence >= 0 AND provider_confidence <= 1)",
            name="ck_preconstruction_findings_provider_confidence",
        ),
        sa.CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="ck_preconstruction_findings_severity",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'needs_review', "
            "'intentional_exclusion', 'superseded')",
            name="ck_preconstruction_findings_status",
        ),
        sa.CheckConstraint(
            "supersedes_finding_id IS NULL OR supersedes_finding_id <> id",
            name="ck_preconstruction_findings_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(["comparison_plan_id"], ["preconstruction_comparison_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["finding_set_id"], ["preconstruction_finding_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_set_id"], ["preconstruction_review_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_finding_id"], ["preconstruction_findings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_set_id", "finding_key", name="uq_preconstruction_findings_set_key"),
    )
    op.create_index("ix_preconstruction_findings_id", "preconstruction_findings", ["id"])
    op.create_index(
        "ix_preconstruction_findings_plan_listing",
        "preconstruction_findings",
        ["project_id", "comparison_plan_id", "status", "severity", "id"],
    )
    op.create_index(
        "ix_preconstruction_findings_set_order",
        "preconstruction_findings",
        ["finding_set_id", "id"],
    )

    op.create_table(
        "preconstruction_finding_assertions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("assertion_id", sa.Integer(), nullable=False),
        sa.Column("assertion_review_id", sa.Integer(), nullable=True),
        sa.Column("side", sa.String(length=24), nullable=False),
        sa.Column("link_role", sa.String(length=24), server_default=sa.text("'primary'"), nullable=False),
        sa.Column("match_class", sa.String(length=16), server_default=sa.text("'none'"), nullable=False),
        sa.Column("match_reasons", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "link_role IN ('primary', 'supporting', 'contradictory', 'near_match')",
            name="ck_preconstruction_finding_assertions_role",
        ),
        sa.CheckConstraint(
            "match_class IN ('exact', 'strong', 'partial', 'weak', 'none')",
            name="ck_preconstruction_finding_assertions_match_class",
        ),
        sa.CheckConstraint(
            "side IN ('requirement', 'coverage', 'context', 'prior_revision', "
            "'current_revision')",
            name="ck_preconstruction_finding_assertions_side",
        ),
        sa.ForeignKeyConstraint(["assertion_id"], ["preconstruction_scope_assertions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assertion_review_id"], ["preconstruction_assertion_reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["preconstruction_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "finding_id", "assertion_id", "side",
            name="uq_preconstruction_finding_assertions_finding_assertion_side",
        ),
    )
    op.create_index("ix_preconstruction_finding_assertions_id", "preconstruction_finding_assertions", ["id"])
    op.create_index(
        "ix_preconstruction_finding_assertions_finding_order",
        "preconstruction_finding_assertions",
        ["finding_id", "side", "assertion_id"],
    )

    op.create_table(
        "preconstruction_finding_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("assertion_id", sa.Integer(), nullable=False),
        sa.Column("assertion_evidence_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("content_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("content_page_id", sa.Integer(), nullable=False),
        sa.Column("content_segment_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("excerpt", sa.String(length=600), nullable=False),
        sa.Column("evidence_role", sa.String(length=24), server_default=sa.text("'primary'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "evidence_role IN ('primary', 'supporting', 'contextual', 'contradictory')",
            name="ck_preconstruction_finding_evidence_role",
        ),
        sa.CheckConstraint(
            "length(excerpt) >= 1 AND length(excerpt) <= 600",
            name="ck_preconstruction_finding_evidence_excerpt_length",
        ),
        sa.CheckConstraint("length(text_hash) = 64", name="ck_preconstruction_finding_evidence_hash_length"),
        sa.CheckConstraint(
            "page_number >= 1 AND segment_index >= 0",
            name="ck_preconstruction_finding_evidence_coordinates",
        ),
        sa.ForeignKeyConstraint(["assertion_evidence_id"], ["preconstruction_assertion_evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assertion_id"], ["preconstruction_scope_assertions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["content_page_id"], ["preconstruction_content_pages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["content_segment_id"], ["preconstruction_content_segments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["content_snapshot_id"], ["preconstruction_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["finding_id"], ["preconstruction_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["preconstruction_review_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "finding_id", "assertion_evidence_id", "evidence_role",
            name="uq_preconstruction_finding_evidence_source_role",
        ),
    )
    op.create_index("ix_preconstruction_finding_evidence_id", "preconstruction_finding_evidence", ["id"])
    op.create_index(
        "ix_preconstruction_finding_evidence_finding_order",
        "preconstruction_finding_evidence",
        ["finding_id", "page_number", "segment_index", "id"],
    )

    op.create_table(
        "preconstruction_finding_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("reviewer_note", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("previous_review_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('accepted', 'rejected', 'needs_review', 'intentional_exclusion')",
            name="ck_preconstruction_finding_reviews_decision",
        ),
        sa.CheckConstraint(
            "previous_review_id IS NULL OR previous_review_id <> id",
            name="ck_preconstruction_finding_reviews_not_self_previous",
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN ('confirmed_gap', "
            "'confirmed_conflict', 'intentional_exclusion', 'covered_elsewhere', "
            "'duplicate', 'incorrect_match', 'insufficient_evidence', "
            "'wrong_comparison_type', 'superseded_source', 'not_applicable', "
            "'requires_trade_review', 'requires_legal_review', 'other')",
            name="ck_preconstruction_finding_reviews_reason",
        ),
        sa.CheckConstraint(
            "reviewer_note IS NULL OR length(reviewer_note) <= 2000",
            name="ck_preconstruction_finding_reviews_note_length",
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["preconstruction_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["previous_review_id"], ["preconstruction_finding_reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preconstruction_finding_reviews_id", "preconstruction_finding_reviews", ["id"])
    op.create_index(
        "ix_preconstruction_finding_reviews_finding_order",
        "preconstruction_finding_reviews",
        ["finding_id", "reviewed_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_preconstruction_finding_reviews_finding_order", table_name="preconstruction_finding_reviews")
    op.drop_index("ix_preconstruction_finding_reviews_id", table_name="preconstruction_finding_reviews")
    op.drop_table("preconstruction_finding_reviews")
    op.drop_index("ix_preconstruction_finding_evidence_finding_order", table_name="preconstruction_finding_evidence")
    op.drop_index("ix_preconstruction_finding_evidence_id", table_name="preconstruction_finding_evidence")
    op.drop_table("preconstruction_finding_evidence")
    op.drop_index("ix_preconstruction_finding_assertions_finding_order", table_name="preconstruction_finding_assertions")
    op.drop_index("ix_preconstruction_finding_assertions_id", table_name="preconstruction_finding_assertions")
    op.drop_table("preconstruction_finding_assertions")
    op.drop_index("ix_preconstruction_findings_set_order", table_name="preconstruction_findings")
    op.drop_index("ix_preconstruction_findings_plan_listing", table_name="preconstruction_findings")
    op.drop_index("ix_preconstruction_findings_id", table_name="preconstruction_findings")
    op.drop_table("preconstruction_findings")
    op.drop_index("ix_preconstruction_finding_sets_plan_listing", table_name="preconstruction_finding_sets")
    op.drop_index("ix_preconstruction_finding_sets_id", table_name="preconstruction_finding_sets")
    op.drop_table("preconstruction_finding_sets")
    op.drop_index("ix_preconstruction_comparison_plans_listing", table_name="preconstruction_comparison_plans")
    op.drop_index("ix_preconstruction_comparison_plans_id", table_name="preconstruction_comparison_plans")
    op.drop_table("preconstruction_comparison_plans")
    with op.batch_alter_table("preconstruction_analysis_runs") as batch_op:
        batch_op.drop_constraint("ck_preconstruction_analysis_runs_type", type_="check")
        batch_op.create_check_constraint(
            "ck_preconstruction_analysis_runs_type",
            "analysis_type IN ('readiness_probe', 'provider_contract_validation', "
            "'content_contract_validation', 'scope_assertion_extraction')",
        )
