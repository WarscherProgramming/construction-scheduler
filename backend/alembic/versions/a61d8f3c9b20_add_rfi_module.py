"""Add project-scoped RFIs and numbering sequences.

Revision ID: a61d8f3c9b20
Revises: 7c2f4a9d1e30
Create Date: 2026-07-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a61d8f3c9b20"
down_revision: str | Sequence[str] | None = "7c2f4a9d1e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rfi_number_sequences",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "rfis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("responsible_company", sa.String(), nullable=True),
        sa.Column("submitted_date", sa.String(), nullable=False),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
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
            name="uq_rfis_project_id_number",
        ),
    )
    op.create_index("ix_rfis_id", "rfis", ["id"])


def downgrade() -> None:
    op.drop_index("ix_rfis_id", table_name="rfis")
    op.drop_table("rfis")
    op.drop_table("rfi_number_sequences")
