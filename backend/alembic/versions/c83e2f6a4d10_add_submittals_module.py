"""Add project-scoped submittals and numbering sequences.

Revision ID: c83e2f6a4d10
Revises: a61d8f3c9b20
Create Date: 2026-07-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c83e2f6a4d10"
down_revision: str | Sequence[str] | None = "a61d8f3c9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "submittal_number_sequences",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "submittals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("specification_section", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("responsible_company", sa.String(), nullable=True),
        sa.Column("submitted_date", sa.String(), nullable=True),
        sa.Column("required_by_date", sa.String(), nullable=True),
        sa.Column("reviewed_date", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reviewer", sa.String(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
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
            name="uq_submittals_project_id_number",
        ),
    )
    op.create_index("ix_submittals_id", "submittals", ["id"])


def downgrade() -> None:
    op.drop_index("ix_submittals_id", table_name="submittals")
    op.drop_table("submittals")
    op.drop_table("submittal_number_sequences")
