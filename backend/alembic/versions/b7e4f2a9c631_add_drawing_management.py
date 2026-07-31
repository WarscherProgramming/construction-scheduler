"""Add construction drawing management.

Revision ID: b7e4f2a9c631
Revises: a6d3e9f1b742
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4f2a9c631"
down_revision: str | Sequence[str] | None = "a6d3e9f1b742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drawing_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("issue_date", sa.String(length=10), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_drawing_sets_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_sets_id", "drawing_sets", ["id"])
    op.create_index(
        "uq_drawing_sets_active_name",
        "drawing_sets",
        ["project_id", "name"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_drawing_sets_project_listing",
        "drawing_sets",
        ["project_id", "deleted_at", "updated_at", "id"],
    )

    op.create_table(
        "drawing_sheets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("drawing_set_id", sa.Integer(), nullable=False),
        sa.Column("sheet_number", sa.String(length=100), nullable=False),
        sa.Column(
            "normalized_sheet_number",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("discipline", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_key", sa.String(length=500), nullable=False),
        sa.Column("current_revision_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "status IN ('active', 'void', 'archived')",
            name="ck_drawing_sheets_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["drawing_set_id"],
            ["drawing_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drawing_set_id",
            "normalized_sheet_number",
            name="uq_drawing_sheets_set_normalized_number",
        ),
    )
    op.create_index("ix_drawing_sheets_id", "drawing_sheets", ["id"])
    op.create_index(
        "ix_drawing_sheets_project_register",
        "drawing_sheets",
        [
            "project_id",
            "deleted_at",
            "drawing_set_id",
            "discipline",
            "status",
            "sort_key",
            "id",
        ],
    )

    op.create_table(
        "drawing_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("drawing_sheet_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("revision_code", sa.String(length=50), nullable=False),
        sa.Column(
            "normalized_revision_code",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("revision_date", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "superseded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "superseded_by_revision_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_drawing_revisions_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["drawing_sheet_id"],
            ["drawing_sheets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_revision_id"],
            ["drawing_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            name="uq_drawing_revisions_document",
        ),
        sa.UniqueConstraint(
            "drawing_sheet_id",
            "normalized_revision_code",
            name="uq_drawing_revisions_sheet_code",
        ),
        sa.UniqueConstraint(
            "drawing_sheet_id",
            "sequence_number",
            name="uq_drawing_revisions_sheet_sequence",
        ),
    )
    op.create_index(
        "ix_drawing_revisions_id", "drawing_revisions", ["id"]
    )
    op.create_index(
        "uq_drawing_revisions_current_sheet",
        "drawing_revisions",
        ["drawing_sheet_id"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_drawing_revisions_sheet_history",
        "drawing_revisions",
        ["drawing_sheet_id", "sequence_number", "id"],
    )
    op.create_index(
        "ix_drawing_revisions_project_document",
        "drawing_revisions",
        ["project_id", "document_id"],
    )

    op.create_table(
        "drawing_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("drawing_set_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("issue_number", sa.String(length=100), nullable=False),
        sa.Column("issue_date", sa.String(length=10), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'void')",
            name="ck_drawing_issues_status",
        ),
        sa.CheckConstraint(
            "purpose IN ('bid', 'permit', 'construction', 'addendum', "
            "'bulletin', 'record', 'as_built', 'other')",
            name="ck_drawing_issues_purpose",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["drawing_set_id"],
            ["drawing_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drawing_set_id",
            "issue_number",
            name="uq_drawing_issues_set_number",
        ),
    )
    op.create_index("ix_drawing_issues_id", "drawing_issues", ["id"])
    op.create_index(
        "ix_drawing_issues_set_listing",
        "drawing_issues",
        ["drawing_set_id", "deleted_at", "issue_date", "id"],
    )

    op.create_table(
        "drawing_issue_revisions",
        sa.Column("drawing_issue_id", sa.Integer(), nullable=False),
        sa.Column("drawing_revision_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["drawing_issue_id"],
            ["drawing_issues.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["drawing_revision_id"],
            ["drawing_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "drawing_issue_id",
            "drawing_revision_id",
        ),
        sa.UniqueConstraint(
            "drawing_issue_id",
            "drawing_revision_id",
            name="uq_drawing_issue_revisions_membership",
        ),
    )
    op.create_index(
        "ix_drawing_issue_revisions_revision",
        "drawing_issue_revisions",
        ["drawing_revision_id", "drawing_issue_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_drawing_issue_revisions_revision",
        table_name="drawing_issue_revisions",
    )
    op.drop_table("drawing_issue_revisions")

    op.drop_index(
        "ix_drawing_issues_set_listing", table_name="drawing_issues"
    )
    op.drop_index("ix_drawing_issues_id", table_name="drawing_issues")
    op.drop_table("drawing_issues")

    op.drop_index(
        "ix_drawing_revisions_project_document",
        table_name="drawing_revisions",
    )
    op.drop_index(
        "ix_drawing_revisions_sheet_history",
        table_name="drawing_revisions",
    )
    op.drop_index(
        "uq_drawing_revisions_current_sheet",
        table_name="drawing_revisions",
    )
    op.drop_index(
        "ix_drawing_revisions_id", table_name="drawing_revisions"
    )
    op.drop_table("drawing_revisions")

    op.drop_index(
        "ix_drawing_sheets_project_register",
        table_name="drawing_sheets",
    )
    op.drop_index("ix_drawing_sheets_id", table_name="drawing_sheets")
    op.drop_table("drawing_sheets")

    op.drop_index(
        "ix_drawing_sets_project_listing", table_name="drawing_sets"
    )
    op.drop_index(
        "uq_drawing_sets_active_name", table_name="drawing_sets"
    )
    op.drop_index("ix_drawing_sets_id", table_name="drawing_sets")
    op.drop_table("drawing_sets")
