"""Add milestones, constraints, and normalized schedule dependencies.

Revision ID: d4e8a1c7f925
Revises: c8d4f1a7b903
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8a1c7f925"
down_revision: str | Sequence[str] | None = "c8d4f1a7b903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_TYPES = "'ASAP', 'ALAP', 'SNET', 'SNLT', 'FNET', 'FNLT', 'MS', 'MF'"
DEPENDENCY_TYPES = "'FS', 'SS', 'FF', 'SF'"


def _add_planning_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_milestone",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "constraint_type",
                sa.String(length=4),
                nullable=True,
                server_default=sa.text("'ASAP'"),
            )
        )
        batch_op.add_column(
            sa.Column("constraint_date", sa.String(), nullable=True)
        )


def _require_planning_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            "is_milestone",
            existing_type=sa.Boolean(),
            existing_server_default=sa.text("false"),
            nullable=False,
        )
        batch_op.alter_column(
            "constraint_type",
            existing_type=sa.String(length=4),
            existing_server_default=sa.text("'ASAP'"),
            nullable=False,
        )


def _create_planning_constraints(table_name: str, prefix: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_check_constraint(
            f"ck_{prefix}_milestone_duration",
            "(is_milestone AND duration = 0) OR "
            "(NOT is_milestone AND duration >= 1)",
        )
        batch_op.create_check_constraint(
            f"ck_{prefix}_constraint_type",
            f"constraint_type IN ({CONSTRAINT_TYPES})",
        )
        batch_op.create_check_constraint(
            f"ck_{prefix}_constraint_date_required",
            "(constraint_type IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NULL) OR "
            "(constraint_type NOT IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NOT NULL)",
        )


def upgrade() -> None:
    _add_planning_columns("tasks")
    _add_planning_columns("schedule_template_tasks")
    _add_planning_columns("schedule_baseline_tasks")

    for table_name in (
        "tasks",
        "schedule_template_tasks",
        "schedule_baseline_tasks",
    ):
        op.execute(
            sa.text(
                f"UPDATE {table_name} "
                "SET is_milestone = false, constraint_type = 'ASAP', "
                "constraint_date = NULL"
            )
        )
        _require_planning_columns(table_name)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_tasks_duration_range", type_="check")
        batch_op.drop_constraint("ck_tasks_lag_days_range", type_="check")
        batch_op.drop_constraint("ck_tasks_dependency_type", type_="check")
        batch_op.drop_constraint(
            "ck_tasks_progress_state_consistency",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_tasks_duration_range",
            "duration >= 0 AND duration <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_tasks_lag_days_range",
            "lag_days >= -36500 AND lag_days <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_tasks_dependency_type",
            f"dependency_type IN ({DEPENDENCY_TYPES})",
        )
        batch_op.create_check_constraint(
            "ck_tasks_progress_state_consistency",
            "(progress_status = 'not_started' "
            "AND percent_complete = 0 "
            "AND actual_start_date IS NULL "
            "AND actual_finish_date IS NULL "
            "AND ((is_milestone AND remaining_duration = 0) "
            "OR (NOT is_milestone AND remaining_duration >= 1))) "
            "OR (progress_status = 'in_progress' "
            "AND NOT is_milestone "
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
    _create_planning_constraints("tasks", "tasks")

    with op.batch_alter_table("schedule_baseline_tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_duration_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_lag_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_dependency_type",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_float_nonnegative",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_duration_range",
            "duration >= 0 AND duration <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_lag_range",
            "lag_days >= -36500 AND lag_days <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_dependency_type",
            f"dependency_type IN ({DEPENDENCY_TYPES})",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_float_range",
            "total_float IS NULL OR "
            "(total_float >= -36500 AND total_float <= 36500)",
        )
    _create_planning_constraints(
        "schedule_baseline_tasks",
        "schedule_baseline_tasks",
    )
    _create_planning_constraints(
        "schedule_template_tasks",
        "schedule_template_tasks",
    )
    with op.batch_alter_table("schedule_template_tasks") as batch_op:
        batch_op.create_check_constraint(
            "ck_schedule_template_tasks_duration_range",
            "duration >= 0 AND duration <= 36500",
        )

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "predecessor_task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dependency_type", sa.String(length=2), nullable=False),
        sa.Column(
            "lag_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.CheckConstraint(
            "task_id <> predecessor_task_id",
            name="ck_task_dependencies_not_self",
        ),
        sa.CheckConstraint(
            f"dependency_type IN ({DEPENDENCY_TYPES})",
            name="ck_task_dependencies_type",
        ),
        sa.CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_task_dependencies_lag_range",
        ),
        sa.UniqueConstraint(
            "task_id",
            "predecessor_task_id",
            name="uq_task_dependencies_task_predecessor",
        ),
    )
    op.create_index(
        "ix_task_dependencies_id",
        "task_dependencies",
        ["id"],
    )
    op.create_index(
        "ix_task_dependencies_project_task",
        "task_dependencies",
        ["project_id", "task_id"],
    )
    op.create_index(
        "ix_task_dependencies_project_predecessor",
        "task_dependencies",
        ["project_id", "predecessor_task_id"],
    )

    op.create_table(
        "schedule_template_task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("schedule_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_task_id",
            sa.Integer(),
            sa.ForeignKey("schedule_template_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "predecessor_template_task_id",
            sa.Integer(),
            sa.ForeignKey("schedule_template_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dependency_type", sa.String(length=2), nullable=False),
        sa.Column(
            "lag_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.CheckConstraint(
            "template_task_id <> predecessor_template_task_id",
            name="ck_template_task_dependencies_not_self",
        ),
        sa.CheckConstraint(
            f"dependency_type IN ({DEPENDENCY_TYPES})",
            name="ck_template_task_dependencies_type",
        ),
        sa.CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_template_task_dependencies_lag_range",
        ),
        sa.UniqueConstraint(
            "template_task_id",
            "predecessor_template_task_id",
            name="uq_template_task_dependencies_pair",
        ),
    )
    op.create_index(
        "ix_schedule_template_task_dependencies_id",
        "schedule_template_task_dependencies",
        ["id"],
    )
    op.create_index(
        "ix_template_task_dependencies_task",
        "schedule_template_task_dependencies",
        ["template_id", "template_task_id"],
    )

    op.create_table(
        "schedule_baseline_task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.Integer(),
            sa.ForeignKey("schedule_baselines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "baseline_task_id",
            sa.Integer(),
            sa.ForeignKey("schedule_baseline_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_task_id", sa.Integer(), nullable=False),
        sa.Column("dependency_type", sa.String(length=2), nullable=False),
        sa.Column("lag_days", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "task_id <> predecessor_task_id",
            name="ck_baseline_task_dependencies_not_self",
        ),
        sa.CheckConstraint(
            f"dependency_type IN ({DEPENDENCY_TYPES})",
            name="ck_baseline_task_dependencies_type",
        ),
        sa.CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_baseline_task_dependencies_lag_range",
        ),
        sa.UniqueConstraint(
            "baseline_task_id",
            "predecessor_task_id",
            name="uq_baseline_task_dependencies_pair",
        ),
    )
    op.create_index(
        "ix_schedule_baseline_task_dependencies_id",
        "schedule_baseline_task_dependencies",
        ["id"],
    )
    op.create_index(
        "ix_baseline_task_dependencies_task",
        "schedule_baseline_task_dependencies",
        ["baseline_id", "baseline_task_id"],
    )

    op.execute(
        """
        INSERT INTO task_dependencies (
            project_id, task_id, predecessor_task_id,
            dependency_type, lag_days
        )
        SELECT project_id, id, predecessor_task_id, dependency_type, lag_days
        FROM tasks
        WHERE predecessor_task_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO schedule_template_task_dependencies (
            template_id, template_task_id, predecessor_template_task_id,
            dependency_type, lag_days
        )
        SELECT template_id, id, predecessor_template_task_id,
               dependency_type, lag_days
        FROM schedule_template_tasks
        WHERE predecessor_template_task_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO schedule_baseline_task_dependencies (
            baseline_id, project_id, baseline_task_id, task_id,
            predecessor_task_id, dependency_type, lag_days
        )
        SELECT baseline_id, project_id, id, task_id,
               predecessor_task_id, dependency_type, lag_days
        FROM schedule_baseline_tasks
        WHERE predecessor_task_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_baseline_task_dependencies_task",
        table_name="schedule_baseline_task_dependencies",
    )
    op.drop_index(
        "ix_schedule_baseline_task_dependencies_id",
        table_name="schedule_baseline_task_dependencies",
    )
    op.drop_table("schedule_baseline_task_dependencies")
    op.drop_index(
        "ix_template_task_dependencies_task",
        table_name="schedule_template_task_dependencies",
    )
    op.drop_index(
        "ix_schedule_template_task_dependencies_id",
        table_name="schedule_template_task_dependencies",
    )
    op.drop_table("schedule_template_task_dependencies")
    op.drop_index(
        "ix_task_dependencies_project_predecessor",
        table_name="task_dependencies",
    )
    op.drop_index(
        "ix_task_dependencies_project_task",
        table_name="task_dependencies",
    )
    op.drop_index("ix_task_dependencies_id", table_name="task_dependencies")
    op.drop_table("task_dependencies")

    op.execute(
        """
        UPDATE tasks
        SET duration = CASE WHEN duration = 0 THEN 1 ELSE duration END,
            remaining_duration = CASE
                WHEN progress_status = 'not_started' AND remaining_duration = 0
                THEN 1 ELSE remaining_duration END,
            dependency_type = CASE
                WHEN dependency_type IN ('FF', 'SF') THEN 'FS'
                ELSE dependency_type END,
            lag_days = CASE WHEN lag_days < 0 THEN 0 ELSE lag_days END,
            is_milestone = false,
            constraint_type = 'ASAP',
            constraint_date = NULL
        """
    )
    for table_name in (
        "schedule_template_tasks",
        "schedule_baseline_tasks",
    ):
        op.execute(
            sa.text(
                f"UPDATE {table_name} "
                "SET duration = CASE WHEN duration = 0 THEN 1 ELSE duration END, "
                "dependency_type = CASE "
                "WHEN dependency_type IN ('FF', 'SF') THEN 'FS' "
                "ELSE dependency_type END, "
                "lag_days = CASE WHEN lag_days < 0 THEN 0 ELSE lag_days END, "
                "is_milestone = false, constraint_type = 'ASAP', "
                "constraint_date = NULL"
            )
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_tasks_constraint_date_required",
            type_="check",
        )
        batch_op.drop_constraint("ck_tasks_constraint_type", type_="check")
        batch_op.drop_constraint("ck_tasks_milestone_duration", type_="check")
        batch_op.drop_constraint("ck_tasks_duration_range", type_="check")
        batch_op.drop_constraint("ck_tasks_lag_days_range", type_="check")
        batch_op.drop_constraint("ck_tasks_dependency_type", type_="check")
        batch_op.drop_constraint(
            "ck_tasks_progress_state_consistency",
            type_="check",
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

    with op.batch_alter_table("schedule_baseline_tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_constraint_date_required",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_constraint_type",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_milestone_duration",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_duration_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_lag_range",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_dependency_type",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_baseline_tasks_float_range",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_duration_range",
            "duration >= 1 AND duration <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_lag_range",
            "lag_days >= 0 AND lag_days <= 36500",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_dependency_type",
            "dependency_type IN ('FS', 'SS')",
        )
        batch_op.create_check_constraint(
            "ck_schedule_baseline_tasks_float_nonnegative",
            "total_float IS NULL OR total_float >= 0",
        )

    with op.batch_alter_table("schedule_template_tasks") as batch_op:
        batch_op.drop_constraint(
            "ck_schedule_template_tasks_constraint_date_required",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_template_tasks_constraint_type",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_template_tasks_milestone_duration",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_schedule_template_tasks_duration_range",
            type_="check",
        )

    for table_name in (
        "tasks",
        "schedule_template_tasks",
        "schedule_baseline_tasks",
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("constraint_date")
            batch_op.drop_column("constraint_type")
            batch_op.drop_column("is_milestone")
