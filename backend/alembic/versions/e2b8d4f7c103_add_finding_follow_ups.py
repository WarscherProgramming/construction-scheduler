"""Add human-initiated follow-up actions for accepted scope findings.

Revision ID: e2b8d4f7c103
Revises: d5a3f9c14e28
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e2b8d4f7c103"
down_revision: str | Sequence[str] | None = "d5a3f9c14e28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACTION_TYPE_SQL = (
    "action_type IN ('rfi', 'change_order', 'submittal', "
    "'procurement_action', 'subcontract_clarification', 'internal_follow_up')"
)
STATUS_SQL = "status IN ('planned', 'linked', 'completed', 'cancelled')"
TARGET_TYPE_SQL = (
    "target_type IS NULL OR target_type IN ('rfi', 'submittal', 'change_order')"
)


def upgrade() -> None:
    op.create_table(
        "preconstruction_finding_follow_ups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("review_set_id", sa.Integer(), nullable=False),
        sa.Column("comparison_plan_id", sa.Integer(), nullable=False),
        sa.Column("finding_review_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("draft_title", sa.String(length=200), nullable=False),
        sa.Column("draft_body", sa.String(length=4000), nullable=False),
        sa.Column("draft_template_version", sa.String(length=100), nullable=False),
        sa.Column("closure_note", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("linked_by", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            ACTION_TYPE_SQL,
            name="ck_preconstruction_finding_follow_ups_action",
        ),
        sa.CheckConstraint(
            STATUS_SQL,
            name="ck_preconstruction_finding_follow_ups_status",
        ),
        sa.CheckConstraint(
            TARGET_TYPE_SQL,
            name="ck_preconstruction_finding_follow_ups_target_type",
        ),
        sa.CheckConstraint(
            "(target_type IS NULL AND target_id IS NULL) OR "
            "(target_type IS NOT NULL AND target_id IS NOT NULL AND target_id > 0)",
            name="ck_preconstruction_finding_follow_ups_target_pair",
        ),
        sa.CheckConstraint(
            "status <> 'planned' OR target_type IS NULL",
            name="ck_preconstruction_finding_follow_ups_planned_has_no_target",
        ),
        sa.CheckConstraint(
            "status <> 'linked' OR target_type IS NOT NULL",
            name="ck_preconstruction_finding_follow_ups_linked_has_target",
        ),
        sa.CheckConstraint(
            "length(trim(draft_title)) > 0",
            name="ck_preconstruction_finding_follow_ups_title_nonblank",
        ),
        sa.CheckConstraint(
            "closure_note IS NULL OR length(closure_note) <= 2000",
            name="ck_preconstruction_finding_follow_ups_note_length",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'linked') OR "
            "(closed_at IS NOT NULL AND closed_by IS NOT NULL)",
            name="ck_preconstruction_finding_follow_ups_closure_identity",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["preconstruction_findings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["review_set_id"],
            ["preconstruction_review_sets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_plan_id"],
            ["preconstruction_comparison_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finding_review_id"],
            ["preconstruction_finding_reviews.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_preconstruction_finding_follow_ups_id",
        "preconstruction_finding_follow_ups",
        ["id"],
    )
    op.create_index(
        "uq_preconstruction_finding_follow_ups_active_action",
        "preconstruction_finding_follow_ups",
        ["finding_id", "action_type"],
        unique=True,
        sqlite_where=sa.text("status IN ('planned', 'linked')"),
        postgresql_where=sa.text("status IN ('planned', 'linked')"),
    )
    op.create_index(
        "ix_preconstruction_finding_follow_ups_plan_listing",
        "preconstruction_finding_follow_ups",
        ["project_id", "comparison_plan_id", "status", "id"],
    )
    op.create_index(
        "ix_preconstruction_finding_follow_ups_finding_order",
        "preconstruction_finding_follow_ups",
        ["project_id", "finding_id", "id"],
    )
    op.create_index(
        "ix_preconstruction_finding_follow_ups_target",
        "preconstruction_finding_follow_ups",
        ["project_id", "target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_preconstruction_finding_follow_ups_target",
        table_name="preconstruction_finding_follow_ups",
    )
    op.drop_index(
        "ix_preconstruction_finding_follow_ups_finding_order",
        table_name="preconstruction_finding_follow_ups",
    )
    op.drop_index(
        "ix_preconstruction_finding_follow_ups_plan_listing",
        table_name="preconstruction_finding_follow_ups",
    )
    op.drop_index(
        "uq_preconstruction_finding_follow_ups_active_action",
        table_name="preconstruction_finding_follow_ups",
    )
    op.drop_index(
        "ix_preconstruction_finding_follow_ups_id",
        table_name="preconstruction_finding_follow_ups",
    )
    op.drop_table("preconstruction_finding_follow_ups")
