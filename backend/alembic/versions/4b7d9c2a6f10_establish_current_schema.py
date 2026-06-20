"""Establish the current application schema.

This migration is intentionally adoption-safe for databases that were
previously initialized with SQLAlchemy ``create_all``. Existing tables and
indexes are preserved; missing objects are created.

Revision ID: 4b7d9c2a6f10
Revises: e131e15d3494
Create Date: 2026-06-20
"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa


revision: str = "4b7d9c2a6f10"
down_revision: str | Sequence[str] | None = "e131e15d3494"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    if context.is_offline_mode():
        return set()

    return set(sa.inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()

    inspector = sa.inspect(op.get_bind())
    return {
        index["name"]
        for index in inspector.get_indexes(table_name)
        if index.get("name")
    }


def _create_index_if_missing(
    name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if name not in _index_names(table_name):
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    tables = _table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_users_id", "users", ["id"])
    _create_index_if_missing("ix_users_email", "users", ["email"], unique=True)

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_projects_id", "projects", ["id"])

    if "schedule_templates" not in tables:
        op.create_table(
            "schedule_templates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_schedule_templates_id",
        "schedule_templates",
        ["id"],
    )

    if "tasks" not in tables:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("duration", sa.Integer(), nullable=True),
            sa.Column("predecessor", sa.String(), nullable=True),
            sa.Column("start_date", sa.String(), nullable=True),
            sa.Column("end_date", sa.String(), nullable=True),
            sa.Column("manual_start_date", sa.String(), nullable=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=True),
            sa.Column("parent_task_id", sa.Integer(), nullable=True),
            sa.Column(
                "indent_level",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=True,
            ),
            sa.Column(
                "is_collapsed",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_tasks_id", "tasks", ["id"])

    if "schedule_template_tasks" not in tables:
        op.create_table(
            "schedule_template_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("template_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("duration", sa.Integer(), nullable=False),
            sa.Column("predecessor", sa.String(), nullable=True),
            sa.Column("manual_start_date", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(
                ["template_id"],
                ["schedule_templates.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_schedule_template_tasks_id",
        "schedule_template_tasks",
        ["id"],
    )

    if "daily_logs" not in tables:
        op.create_table(
            "daily_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=False),
            sa.Column("manpower", sa.Integer(), nullable=False),
            sa.Column("work_performed", sa.Text(), nullable=True),
            sa.Column("delays", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_daily_logs_id", "daily_logs", ["id"])

    if "inspections" not in tables:
        op.create_table(
            "inspections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.String(), nullable=False),
            sa.Column("inspection_type", sa.String(), nullable=False),
            sa.Column("inspector", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("corrective_action", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_inspections_id", "inspections", ["id"])

    if "notes_delays" not in tables:
        op.create_table(
            "notes_delays",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.String(), nullable=False),
            sa.Column("entry_type", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("impact", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_notes_delays_id", "notes_delays", ["id"])

    if "change_orders" not in tables:
        op.create_table(
            "change_orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.String(), nullable=False),
            sa.Column("co_number", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("amount", sa.String(), nullable=True),
            sa.Column("responsible_party", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_change_orders_id", "change_orders", ["id"])

    if "project_companies" not in tables:
        op.create_table(
            "project_companies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("trade", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_project_companies_id",
        "project_companies",
        ["id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_companies_id", table_name="project_companies")
    op.drop_table("project_companies")
    op.drop_index("ix_change_orders_id", table_name="change_orders")
    op.drop_table("change_orders")
    op.drop_index("ix_notes_delays_id", table_name="notes_delays")
    op.drop_table("notes_delays")
    op.drop_index("ix_inspections_id", table_name="inspections")
    op.drop_table("inspections")
    op.drop_index("ix_daily_logs_id", table_name="daily_logs")
    op.drop_table("daily_logs")
    op.drop_index(
        "ix_schedule_template_tasks_id",
        table_name="schedule_template_tasks",
    )
    op.drop_table("schedule_template_tasks")
    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(
        "ix_schedule_templates_id",
        table_name="schedule_templates",
    )
    op.drop_table("schedule_templates")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
