"""Add project-scoped punch items and numbering sequences.

Revision ID: d94f7a2b6e31
Revises: c83e2f6a4d10
Create Date: 2026-07-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d94f7a2b6e31"
down_revision: str | Sequence[str] | None = "c83e2f6a4d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "punch_item_number_sequences",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "punch_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("trade", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("responsible_company", sa.String(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("completed_date", sa.String(), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "number",
            name="uq_punch_items_project_id_number",
        ),
    )
    op.create_index("ix_punch_items_id", "punch_items", ["id"])


def downgrade() -> None:
    op.drop_index("ix_punch_items_id", table_name="punch_items")
    op.drop_table("punch_items")
    op.drop_table("punch_item_number_sequences")
