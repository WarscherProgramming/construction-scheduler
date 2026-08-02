"""Add immutable schedule baselines and comparison selection.

Revision ID: a2c7e9f4b610
Revises: f6a1c9d3e742
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a2c7e9f4b610"
down_revision: str | Sequence[str] | None = "f6a1c9d3e742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedule_baselines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("captured_by", sa.Integer(), nullable=False),
        sa.Column("schedule_start_date", sa.String(), nullable=False),
        sa.Column("task_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_schedule_baselines_name_nonblank",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_schedule_baselines_status",
        ),
        sa.CheckConstraint(
            "task_count >= 0",
            name="ck_schedule_baselines_task_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["captured_by"],
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
            name="uq_schedule_baselines_project_normalized_name",
        ),
    )
    op.create_index(
        "ix_schedule_baselines_id",
        "schedule_baselines",
        ["id"],
    )
    op.create_index(
        "ix_schedule_baselines_project_captured",
        "schedule_baselines",
        ["project_id", "captured_at", "id"],
    )
    op.create_index(
        "ix_schedule_baselines_project_status",
        "schedule_baselines",
        ["project_id", "status", "captured_at"],
    )

    op.create_table(
        "schedule_baseline_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("baseline_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("parent_task_id", sa.Integer(), nullable=True),
        sa.Column("predecessor_task_id", sa.Integer(), nullable=True),
        sa.Column("dependency_type", sa.String(length=2), nullable=False),
        sa.Column("lag_days", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("manual_start_date", sa.String(), nullable=True),
        sa.Column("start_date", sa.String(), nullable=True),
        sa.Column("end_date", sa.String(), nullable=True),
        sa.Column("is_summary", sa.Boolean(), nullable=False),
        sa.Column("was_critical", sa.Boolean(), nullable=False),
        sa.Column("total_float", sa.Integer(), nullable=True),
        sa.Column("wbs_path", sa.String(length=10000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "task_id > 0",
            name="ck_schedule_baseline_tasks_task_id_positive",
        ),
        sa.CheckConstraint(
            "duration >= 1 AND duration <= 36500",
            name="ck_schedule_baseline_tasks_duration_range",
        ),
        sa.CheckConstraint(
            "lag_days >= 0 AND lag_days <= 36500",
            name="ck_schedule_baseline_tasks_lag_range",
        ),
        sa.CheckConstraint(
            "dependency_type IN ('FS', 'SS')",
            name="ck_schedule_baseline_tasks_dependency_type",
        ),
        sa.CheckConstraint(
            "order_index IS NULL OR order_index >= 0",
            name="ck_schedule_baseline_tasks_order_nonnegative",
        ),
        sa.CheckConstraint(
            "total_float IS NULL OR total_float >= 0",
            name="ck_schedule_baseline_tasks_float_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_id"],
            ["schedule_baselines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "baseline_id",
            "task_id",
            name="uq_schedule_baseline_tasks_baseline_task",
        ),
    )
    op.create_index(
        "ix_schedule_baseline_tasks_id",
        "schedule_baseline_tasks",
        ["id"],
    )
    op.create_index(
        "ix_schedule_baseline_tasks_baseline_order",
        "schedule_baseline_tasks",
        ["baseline_id", "order_index", "id"],
    )
    op.create_index(
        "ix_schedule_baseline_tasks_baseline_parent",
        "schedule_baseline_tasks",
        ["baseline_id", "parent_task_id"],
    )
    op.create_index(
        "ix_schedule_baseline_tasks_baseline_predecessor",
        "schedule_baseline_tasks",
        ["baseline_id", "predecessor_task_id"],
    )

    with op.batch_alter_table("project_schedule_settings") as batch_op:
        batch_op.add_column(
            sa.Column("comparison_baseline_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_project_schedule_settings_comparison_baseline",
            "schedule_baselines",
            ["comparison_baseline_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_project_schedule_settings_comparison_baseline",
        "project_schedule_settings",
        ["comparison_baseline_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_schedule_settings_comparison_baseline",
        table_name="project_schedule_settings",
    )
    with op.batch_alter_table("project_schedule_settings") as batch_op:
        batch_op.drop_constraint(
            "fk_project_schedule_settings_comparison_baseline",
            type_="foreignkey",
        )
        batch_op.drop_column("comparison_baseline_id")

    op.drop_index(
        "ix_schedule_baseline_tasks_baseline_predecessor",
        table_name="schedule_baseline_tasks",
    )
    op.drop_index(
        "ix_schedule_baseline_tasks_baseline_parent",
        table_name="schedule_baseline_tasks",
    )
    op.drop_index(
        "ix_schedule_baseline_tasks_baseline_order",
        table_name="schedule_baseline_tasks",
    )
    op.drop_index(
        "ix_schedule_baseline_tasks_id",
        table_name="schedule_baseline_tasks",
    )
    op.drop_table("schedule_baseline_tasks")

    op.drop_index(
        "ix_schedule_baselines_project_status",
        table_name="schedule_baselines",
    )
    op.drop_index(
        "ix_schedule_baselines_project_captured",
        table_name="schedule_baselines",
    )
    op.drop_index("ix_schedule_baselines_id", table_name="schedule_baselines")
    op.drop_table("schedule_baselines")
