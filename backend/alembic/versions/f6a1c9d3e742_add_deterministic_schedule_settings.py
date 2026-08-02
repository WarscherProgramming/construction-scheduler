"""Add deterministic project schedule settings and task safeguards.

Revision ID: f6a1c9d3e742
Revises: e4b7c2d9f651
"""

from collections.abc import Sequence
from datetime import date
import re

from alembic import op
import sqlalchemy as sa


revision: str = "f6a1c9d3e742"
down_revision: str | Sequence[str] | None = "e4b7c2d9f651"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def upgrade() -> None:
    op.create_table(
        "project_schedule_settings",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("schedule_start_date", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )

    _backfill_schedule_settings()
    _prepare_task_constraints()

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "duration",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "is_collapsed",
            existing_type=sa.Integer(),
            existing_server_default=sa.text("0"),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_tasks_duration_range",
            "duration >= 1 AND duration <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_tasks_lag_days_range",
            "lag_days >= 0 AND lag_days <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_tasks_dependency_type",
            "dependency_type IN ('FS', 'SS')",
        )
        batch_op.create_check_constraint(
            "ck_tasks_order_index_nonnegative",
            "order_index IS NULL OR order_index >= 0",
        )
        batch_op.create_check_constraint(
            "ck_tasks_is_collapsed",
            "is_collapsed IN (0, 1)",
        )
        batch_op.create_check_constraint(
            "ck_tasks_not_own_predecessor",
            "predecessor_task_id IS NULL OR predecessor_task_id <> id",
        )
        batch_op.create_check_constraint(
            "ck_tasks_not_own_parent",
            "parent_task_id IS NULL OR parent_task_id <> id",
        )

    op.create_index(
        "ix_tasks_project_order_id",
        "tasks",
        ["project_id", "order_index", "id"],
    )
    op.create_index(
        "ix_tasks_project_predecessor",
        "tasks",
        ["project_id", "predecessor_task_id"],
    )
    op.create_index(
        "ix_tasks_project_parent",
        "tasks",
        ["project_id", "parent_task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_project_parent", table_name="tasks")
    op.drop_index("ix_tasks_project_predecessor", table_name="tasks")
    op.drop_index("ix_tasks_project_order_id", table_name="tasks")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_tasks_not_own_parent",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_not_own_predecessor",
            type_="check",
        )
        batch_op.drop_constraint("ck_tasks_is_collapsed", type_="check")
        batch_op.drop_constraint(
            "ck_tasks_order_index_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_dependency_type",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_lag_days_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_tasks_duration_range",
            type_="check",
        )
        batch_op.alter_column(
            "is_collapsed",
            existing_type=sa.Integer(),
            existing_server_default=sa.text("0"),
            nullable=True,
        )
        batch_op.alter_column(
            "duration",
            existing_type=sa.Integer(),
            nullable=True,
        )

    op.drop_table("project_schedule_settings")


def _valid_iso_date(value: object) -> str | None:
    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _backfill_schedule_settings() -> None:
    connection = op.get_bind()
    project_ids = connection.execute(
        sa.text("SELECT id FROM projects ORDER BY id")
    ).scalars()
    task_rows = [
        dict(row)
        for row in connection.execute(
            sa.text(
                """
                SELECT id, project_id, parent_task_id, start_date
                FROM tasks
                ORDER BY project_id, order_index, id
                """
            )
        ).mappings()
    ]
    summary_ids = {
        row["parent_task_id"]
        for row in task_rows
        if row["parent_task_id"] is not None
    }
    migration_fallback = date.today().isoformat()

    for project_id in project_ids:
        project_tasks = [
            row for row in task_rows if row["project_id"] == project_id
        ]
        root_leaf_dates = [
            valid_date
            for row in project_tasks
            if row["parent_task_id"] is None and row["id"] not in summary_ids
            if (valid_date := _valid_iso_date(row["start_date"])) is not None
        ]
        leaf_dates = [
            valid_date
            for row in project_tasks
            if row["id"] not in summary_ids
            if (valid_date := _valid_iso_date(row["start_date"])) is not None
        ]
        schedule_start_date = (
            min(root_leaf_dates)
            if root_leaf_dates
            else min(leaf_dates)
            if leaf_dates
            else migration_fallback
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date
                ) VALUES (
                    :project_id, :schedule_start_date
                )
                """
            ),
            {
                "project_id": project_id,
                "schedule_start_date": schedule_start_date,
            },
        )


def _prepare_task_constraints() -> None:
    connection = op.get_bind()
    invalid_checks = {
        "duration above 36500": "duration > 36500",
        "lag outside 0..36500": (
            "lag_days IS NULL OR lag_days < 0 OR lag_days > 36500"
        ),
        "dependency type outside FS/SS": (
            "dependency_type IS NULL OR dependency_type NOT IN ('FS', 'SS')"
        ),
        "negative order index": "order_index < 0",
        "collapsed value outside 0/1": (
            "is_collapsed IS NOT NULL AND is_collapsed NOT IN (0, 1)"
        ),
        "self predecessor": "predecessor_task_id = id",
        "self parent": "parent_task_id = id",
    }

    for description, condition in invalid_checks.items():
        count = connection.execute(
            sa.text(f"SELECT COUNT(*) FROM tasks WHERE {condition}")
        ).scalar_one()
        if count:
            raise RuntimeError(
                f"Cannot add scheduling constraints: {count} task rows have "
                f"{description}"
            )

    # Legacy zero/null values represented a one-day stored span. One workday
    # is the narrowest compatible value under the established API contract.
    connection.execute(
        sa.text(
            """
            UPDATE tasks
            SET duration = 1
            WHERE duration IS NULL OR duration < 1
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE tasks
            SET is_collapsed = 0
            WHERE is_collapsed IS NULL
            """
        )
    )
