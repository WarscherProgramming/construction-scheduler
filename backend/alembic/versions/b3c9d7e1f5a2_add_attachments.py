"""Add generic project attachment metadata.

Revision ID: b3c9d7e1f5a2
Revises: f2a8c1d4e6b0
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b3c9d7e1f5a2"
down_revision: str | Sequence[str] | None = "f2a8c1d4e6b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("parent_type", sa.String(length=50), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column(
            "storage_provider",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_attachments_size_bytes_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_attachments_storage_key",
        ),
    )
    op.create_index(
        "ix_attachments_id",
        "attachments",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_attachments_parent_listing",
        "attachments",
        [
            "project_id",
            "parent_type",
            "parent_id",
            "created_at",
            "id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attachments_parent_listing",
        table_name="attachments",
    )
    op.drop_index("ix_attachments_id", table_name="attachments")
    op.drop_table("attachments")
