"""Add look-ahead planning.

Revision ID: e6b4c9a2d715
Revises: d4e8a1c7f925
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e6b4c9a2d715"
down_revision: str | Sequence[str] | None = "d4e8a1c7f925"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "look_ahead_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("anchor_date", sa.String(length=10), nullable=False),
        sa.Column(
            "window_days",
            sa.Integer(),
            server_default=sa.text("21"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_look_ahead_plans_name_nonblank",
        ),
        sa.CheckConstraint(
            "window_days >= 7 AND window_days <= 42",
            name="ck_look_ahead_plans_window_days",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_look_ahead_plans_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_look_ahead_plans_project_name",
        ),
    )
    op.create_index(
        "ix_look_ahead_plans_id",
        "look_ahead_plans",
        ["id"],
    )
    op.create_index(
        "ix_look_ahead_plans_project_created",
        "look_ahead_plans",
        ["project_id", "created_at", "id"],
    )
    op.create_index(
        "ix_look_ahead_plans_project_status_anchor",
        "look_ahead_plans",
        ["project_id", "status", "anchor_date", "id"],
    )

    op.create_table(
        "look_ahead_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("look_ahead_plan_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "readiness_status",
            sa.String(length=16),
            server_default=sa.text("'unreviewed'"),
            nullable=False,
        ),
        sa.Column("blocking_reason", sa.String(length=2000), nullable=True),
        sa.Column("constraint_category", sa.String(length=32), nullable=True),
        sa.Column("constraint_owner", sa.String(length=255), nullable=True),
        sa.Column("target_resolution_date", sa.String(length=10), nullable=True),
        sa.Column("commitment_note", sa.String(length=2000), nullable=True),
        sa.Column("responsible_company_id", sa.Integer(), nullable=True),
        sa.Column(
            "manually_included",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "manually_excluded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("override_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "readiness_status IN "
            "('unreviewed', 'ready', 'at_risk', 'blocked', "
            "'committed', 'complete')",
            name="ck_look_ahead_items_readiness",
        ),
        sa.CheckConstraint(
            "constraint_category IS NULL OR constraint_category IN "
            "('predecessor_work', 'design_information', 'submittal', "
            "'material', 'labor', 'equipment', 'access', 'inspection', "
            "'permit', 'owner_decision', 'safety', 'weather', 'other')",
            name="ck_look_ahead_items_constraint_category",
        ),
        sa.CheckConstraint(
            "NOT (manually_included AND manually_excluded)",
            name="ck_look_ahead_items_manual_flags",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["look_ahead_plan_id"],
            ["look_ahead_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["responsible_company_id"],
            ["project_companies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "look_ahead_plan_id",
            "task_id",
            name="uq_look_ahead_items_plan_task",
        ),
    )
    op.create_index(
        "ix_look_ahead_items_id",
        "look_ahead_items",
        ["id"],
    )
    op.create_index(
        "ix_look_ahead_items_plan_readiness",
        "look_ahead_items",
        ["look_ahead_plan_id", "readiness_status"],
    )
    op.create_index(
        "ix_look_ahead_items_project_task",
        "look_ahead_items",
        ["project_id", "task_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_look_ahead_items_project_task",
        table_name="look_ahead_items",
    )
    op.drop_index(
        "ix_look_ahead_items_plan_readiness",
        table_name="look_ahead_items",
    )
    op.drop_index("ix_look_ahead_items_id", table_name="look_ahead_items")
    op.drop_table("look_ahead_items")
    op.drop_index(
        "ix_look_ahead_plans_project_status_anchor",
        table_name="look_ahead_plans",
    )
    op.drop_index(
        "ix_look_ahead_plans_project_created",
        table_name="look_ahead_plans",
    )
    op.drop_index("ix_look_ahead_plans_id", table_name="look_ahead_plans")
    op.drop_table("look_ahead_plans")
