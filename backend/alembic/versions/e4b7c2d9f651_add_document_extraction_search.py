"""Add document text extraction and page search storage.

Revision ID: e4b7c2d9f651
Revises: d9a2f5c8e173
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e4b7c2d9f651"
down_revision: str | Sequence[str] | None = "d9a2f5c8e173"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EXTRACTION_STATUSES = (
    "'pending', 'processing', 'completed', 'completed_with_warnings', "
    "'failed', 'unavailable', 'cancelled'"
)
EXTRACTION_METHODS = (
    "'embedded_text', 'ocr', 'mixed', 'metadata_only', 'unavailable'"
)


def upgrade() -> None:
    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "extraction_method",
            sa.String(length=32),
            server_default="unavailable",
            nullable=False,
        ),
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "pages_processed",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "text_character_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "searchable",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "language",
            sa.String(length=16),
            server_default="eng",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.String(length=300), nullable=True),
        sa.Column("warning_codes", sa.String(length=300), nullable=True),
        sa.Column("extractor_version", sa.String(length=100), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint(
            f"status IN ({EXTRACTION_STATUSES})",
            name="ck_document_extractions_status",
        ),
        sa.CheckConstraint(
            f"extraction_method IN ({EXTRACTION_METHODS})",
            name="ck_document_extractions_method",
        ),
        sa.CheckConstraint(
            "page_count >= 0",
            name="ck_document_extractions_page_count_nonnegative",
        ),
        sa.CheckConstraint(
            "pages_processed >= 0 AND pages_processed <= page_count",
            name="ck_document_extractions_pages_processed",
        ),
        sa.CheckConstraint(
            "text_character_count >= 0",
            name="ck_document_extractions_character_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            name="uq_document_extractions_document",
        ),
    )
    op.create_index(
        "ix_document_extractions_id",
        "document_extractions",
        ["id"],
    )
    op.create_index(
        "ix_document_extractions_project_status",
        "document_extractions",
        ["project_id", "status", "searchable", "updated_at", "id"],
    )
    op.create_index(
        "ix_document_extractions_project_document",
        "document_extractions",
        ["project_id", "document_id"],
    )

    search_vector_type = (
        postgresql.TSVECTOR()
        if op.get_bind().dialect.name == "postgresql"
        else sa.Text()
    )
    op.create_table(
        "document_page_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("search_vector", search_vector_type, nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "page_number >= 1",
            name="ck_document_page_texts_page_positive",
        ),
        sa.CheckConstraint(
            f"extraction_method IN ({EXTRACTION_METHODS})",
            name="ck_document_page_texts_method",
        ),
        sa.CheckConstraint(
            "character_count >= 0",
            name="ck_document_page_texts_character_count_nonnegative",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_document_page_texts_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"],
            ["document_extractions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extraction_id",
            "page_number",
            name="uq_document_page_texts_extraction_page",
        ),
    )
    op.create_index(
        "ix_document_page_texts_id",
        "document_page_texts",
        ["id"],
    )
    op.create_index(
        "ix_document_page_texts_project_document",
        "document_page_texts",
        ["project_id", "document_id", "page_number", "id"],
    )
    op.create_index(
        "ix_document_page_texts_search_vector",
        "document_page_texts",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "document_extraction_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=50), nullable=True),
        sa.Column("last_error_message", sa.String(length=300), nullable=True),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=100), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', "
            "'cancelled')",
            name="ck_document_extraction_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_document_extraction_jobs_attempt_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_extraction_jobs_id",
        "document_extraction_jobs",
        ["id"],
    )
    op.create_index(
        "uq_document_extraction_jobs_active_document",
        "document_extraction_jobs",
        ["document_id", "source_checksum"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'processing')"),
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.create_index(
        "ix_document_extraction_jobs_pending",
        "document_extraction_jobs",
        ["status", "available_at", "created_at", "id"],
    )
    op.create_index(
        "ix_document_extraction_jobs_lease",
        "document_extraction_jobs",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_document_extraction_jobs_project_document",
        "document_extraction_jobs",
        ["project_id", "document_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_extraction_jobs_project_document",
        table_name="document_extraction_jobs",
    )
    op.drop_index(
        "ix_document_extraction_jobs_lease",
        table_name="document_extraction_jobs",
    )
    op.drop_index(
        "ix_document_extraction_jobs_pending",
        table_name="document_extraction_jobs",
    )
    op.drop_index(
        "uq_document_extraction_jobs_active_document",
        table_name="document_extraction_jobs",
    )
    op.drop_index(
        "ix_document_extraction_jobs_id",
        table_name="document_extraction_jobs",
    )
    op.drop_table("document_extraction_jobs")

    op.drop_index(
        "ix_document_page_texts_search_vector",
        table_name="document_page_texts",
    )
    op.drop_index(
        "ix_document_page_texts_project_document",
        table_name="document_page_texts",
    )
    op.drop_index(
        "ix_document_page_texts_id",
        table_name="document_page_texts",
    )
    op.drop_table("document_page_texts")

    op.drop_index(
        "ix_document_extractions_project_document",
        table_name="document_extractions",
    )
    op.drop_index(
        "ix_document_extractions_project_status",
        table_name="document_extractions",
    )
    op.drop_index(
        "ix_document_extractions_id",
        table_name="document_extractions",
    )
    op.drop_table("document_extractions")
