"""Add schedule progress fields and a persistent project data date.

Revision ID: c8d4f1a7b903
Revises: a2c7e9f4b610
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4f1a7b903"
down_revision: str | Sequence[str] | None = "a2c7e9f4b610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("project_schedule_settings") as batch_op:
        batch_op.add_column(sa.Column("data_date", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE project_schedule_settings
        SET data_date = schedule_start_date
        WHERE data_date IS NULL
        """
    )

    with op.batch_alter_table("project_schedule_settings") as batch_op:
        batch_op.alter_column(
            "data_date",
            existing_type=sa.String(),
            nullable=False,
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "progress_status",
                sa.String(length=16),
                server_default=sa.text("'not_started'"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "percent_complete",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("actual_start_date", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("actual_finish_date", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("remaining_duration", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "status_updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("status_updated_by", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_tasks_status_updated_by_users",
            "users",
            ["status_updated_by"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        """
        UPDATE tasks
        SET progress_status = 'not_started',
            percent_complete = 0,
            remaining_duration = duration,
            actual_start_date = NULL,
            actual_finish_date = NULL,
            status_updated_at = NULL,
            status_updated_by = NULL
        """
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "progress_status",
            existing_type=sa.String(length=16),
            existing_server_default=sa.text("'not_started'"),
            nullable=False,
        )
        batch_op.alter_column(
            "percent_complete",
            existing_type=sa.Integer(),
            existing_server_default=sa.text("0"),
            nullable=False,
        )
        batch_op.alter_column(
            "remaining_duration",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_tasks_progress_status",
            "progress_status IN ('not_started', 'in_progress', 'completed')",
        )
        batch_op.create_check_constraint(
            "ck_tasks_percent_complete_range",
            "percent_complete >= 0 AND percent_complete <= 100",
        )
        batch_op.create_check_constraint(
            "ck_tasks_remaining_duration_range",
            "remaining_duration >= 0 AND remaining_duration <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_tasks_actual_date_order",
            "actual_finish_date IS NULL OR actual_start_date IS NULL "
            "OR actual_finish_date >= actual_start_date",
        )
        batch_op.create_check_constraint(
            "ck_tasks_progress_state_consistency",
            "(progress_status = 'not_started' "
            "AND percent_complete = 0 "
            "AND actual_start_date IS NULL "
            "AND actual_finish_date IS NULL "
            "AND remaining_duration >= 1) "
            "OR (progress_status = 'in_progress' "
            "AND percent_complete BETWEEN 1 AND 99 "
            "AND actual_start_date IS NOT NULL "
            "AND actual_finish_date IS NULL "
            "AND remaining_duration >= 1) "
            "OR (progress_status = 'completed' "
            "AND percent_complete = 100 "
            "AND actual_start_date IS NOT NULL "
            "AND actual_finish_date IS NOT NULL "
            "AND remaining_duration = 0)",
        )

    op.create_index(
        "ix_tasks_project_progress_status",
        "tasks",
        ["project_id", "progress_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_project_progress_status", table_name="tasks")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_tasks_progress_state_consistency",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_actual_date_order",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_remaining_duration_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_percent_complete_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_progress_status",
            type_="check",
        )
        batch_op.drop_constraint(
            "fk_tasks_status_updated_by_users",
            type_="foreignkey",
        )
        batch_op.drop_column("status_updated_by")
        batch_op.drop_column("status_updated_at")
        batch_op.drop_column("remaining_duration")
        batch_op.drop_column("actual_finish_date")
        batch_op.drop_column("actual_start_date")
        batch_op.drop_column("percent_complete")
        batch_op.drop_column("progress_status")

    with op.batch_alter_table("project_schedule_settings") as batch_op:
        batch_op.drop_column("data_date")
