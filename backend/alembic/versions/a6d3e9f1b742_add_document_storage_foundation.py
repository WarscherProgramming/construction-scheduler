"""Add document storage foundation.

Revision ID: a6d3e9f1b742
Revises: f8c2d6e0a315
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a6d3e9f1b742"
down_revision: str | Sequence[str] | None = "f8c2d6e0a315"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("parent_folder_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=2000), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_folder_id"],
            ["folders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "path",
            name="uq_folders_project_path",
        ),
    )
    op.create_index("ix_folders_id", "folders", ["id"], unique=False)
    op.create_index(
        "ix_folders_project_listing",
        "folders",
        ["project_id", "deleted_at", "path", "id"],
        unique=False,
    )
    op.create_index(
        "uq_folders_active_root_name",
        "folders",
        ["project_id", "name"],
        unique=True,
        sqlite_where=sa.text(
            "parent_folder_id IS NULL AND deleted_at IS NULL"
        ),
        postgresql_where=sa.text(
            "parent_folder_id IS NULL AND deleted_at IS NULL"
        ),
    )
    op.create_index(
        "uq_folders_active_child_name",
        "folders",
        ["project_id", "parent_folder_id", "name"],
        unique=True,
        sqlite_where=sa.text(
            "parent_folder_id IS NOT NULL AND deleted_at IS NULL"
        ),
        postgresql_where=sa.text(
            "parent_folder_id IS NOT NULL AND deleted_at IS NULL"
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=True),
        sa.Column("parent_document_id", sa.Integer(), nullable=True),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_provider", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("storage_bucket", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "is_current_version",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.String(length=50),
            server_default="General",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="Active",
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_documents_size_bytes_nonnegative",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_documents_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["folders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_documents_storage_key",
        ),
    )
    op.create_index("ix_documents_id", "documents", ["id"], unique=False)
    op.create_index(
        "ix_documents_project_listing",
        "documents",
        ["project_id", "deleted_at", "folder_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_version_lineage",
        "documents",
        ["parent_document_id", "version", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_version_lineage",
        table_name="documents",
    )
    op.drop_index(
        "ix_documents_project_listing",
        table_name="documents",
    )
    op.drop_index("ix_documents_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index(
        "uq_folders_active_child_name",
        table_name="folders",
    )
    op.drop_index(
        "uq_folders_active_root_name",
        table_name="folders",
    )
    op.drop_index(
        "ix_folders_project_listing",
        table_name="folders",
    )
    op.drop_index("ix_folders_id", table_name="folders")
    op.drop_table("folders")
