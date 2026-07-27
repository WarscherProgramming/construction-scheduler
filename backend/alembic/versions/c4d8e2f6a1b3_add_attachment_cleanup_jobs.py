"""Add durable attachment object cleanup jobs.

Revision ID: c4d8e2f6a1b3
Revises: b3c9d7e1f5a2
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c4d8e2f6a1b3"
down_revision: str | Sequence[str] | None = "b3c9d7e1f5a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACTIVE_JOB_PREDICATE = (
    "status IN ('Pending', 'Processing', 'Failed')"
)


def upgrade() -> None:
    op.create_table(
        "attachment_cleanup_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "storage_provider",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column(
            "operation",
            sa.String(length=20),
            server_default="Delete",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="Pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_attachment_cleanup_jobs_attempt_nonnegative",
        ),
        sa.CheckConstraint(
            "operation = 'Delete'",
            name="ck_attachment_cleanup_jobs_operation",
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('Pending', 'Processing', 'Completed', 'Failed')"
            ),
            name="ck_attachment_cleanup_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["attachments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attachment_cleanup_jobs_id",
        "attachment_cleanup_jobs",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_attachment_cleanup_jobs_lease",
        "attachment_cleanup_jobs",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_attachment_cleanup_jobs_pending",
        "attachment_cleanup_jobs",
        ["status", "next_attempt_at", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "uq_attachment_cleanup_jobs_active_object",
        "attachment_cleanup_jobs",
        ["storage_provider", "storage_key"],
        unique=True,
        sqlite_where=sa.text(ACTIVE_JOB_PREDICATE),
        postgresql_where=sa.text(ACTIVE_JOB_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_attachment_cleanup_jobs_active_object",
        table_name="attachment_cleanup_jobs",
    )
    op.drop_index(
        "ix_attachment_cleanup_jobs_pending",
        table_name="attachment_cleanup_jobs",
    )
    op.drop_index(
        "ix_attachment_cleanup_jobs_lease",
        table_name="attachment_cleanup_jobs",
    )
    op.drop_index(
        "ix_attachment_cleanup_jobs_id",
        table_name="attachment_cleanup_jobs",
    )
    op.drop_table("attachment_cleanup_jobs")
