"""Add construction document relationships.

Revision ID: d9a2f5c8e173
Revises: c8f1a4d7e290
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d9a2f5c8e173"
down_revision: str | Sequence[str] | None = "c8f1a4d7e290"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column(
            "relationship_type",
            sa.String(length=32),
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
            "source_type IN ('document', 'drawing_set', 'drawing_sheet', "
            "'drawing_revision', 'drawing_issue', 'rfi', 'submittal', "
            "'punch_item', 'change_order', 'daily_log')",
            name="ck_entity_relationships_source_type",
        ),
        sa.CheckConstraint(
            "target_type IN ('document', 'drawing_set', 'drawing_sheet', "
            "'drawing_revision', 'drawing_issue', 'rfi', 'submittal', "
            "'punch_item', 'change_order', 'daily_log')",
            name="ck_entity_relationships_target_type",
        ),
        sa.CheckConstraint(
            "relationship_type IN ('references', 'responds_to', "
            "'supersedes', 'supports', 'impacts', 'originated_from', "
            "'resolves', 'documents', 'includes', 'associated_with', "
            "'located_on', 'generated_by')",
            name="ck_entity_relationships_relationship_type",
        ),
        sa.CheckConstraint(
            "source_id > 0",
            name="ck_entity_relationships_source_id_positive",
        ),
        sa.CheckConstraint(
            "target_id > 0",
            name="ck_entity_relationships_target_id_positive",
        ),
        sa.CheckConstraint(
            "NOT (source_type = target_type AND source_id = target_id)",
            name="ck_entity_relationships_distinct_entities",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_entity_relationships_id",
        "entity_relationships",
        ["id"],
    )
    op.create_index(
        "uq_entity_relationships_active_pair",
        "entity_relationships",
        [
            "project_id",
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship_type",
        ],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_entity_relationships_project_source",
        "entity_relationships",
        [
            "project_id",
            "source_type",
            "source_id",
            "deleted_at",
            "created_at",
            "id",
        ],
    )
    op.create_index(
        "ix_entity_relationships_project_target",
        "entity_relationships",
        [
            "project_id",
            "target_type",
            "target_id",
            "deleted_at",
            "created_at",
            "id",
        ],
    )
    op.create_index(
        "ix_entity_relationships_project_type",
        "entity_relationships",
        ["project_id", "relationship_type", "deleted_at"],
    )
    op.create_index(
        "ix_entity_relationships_project_created",
        "entity_relationships",
        ["project_id", "deleted_at", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entity_relationships_project_created",
        table_name="entity_relationships",
    )
    op.drop_index(
        "ix_entity_relationships_project_type",
        table_name="entity_relationships",
    )
    op.drop_index(
        "ix_entity_relationships_project_target",
        table_name="entity_relationships",
    )
    op.drop_index(
        "ix_entity_relationships_project_source",
        table_name="entity_relationships",
    )
    op.drop_index(
        "uq_entity_relationships_active_pair",
        table_name="entity_relationships",
    )
    op.drop_index(
        "ix_entity_relationships_id",
        table_name="entity_relationships",
    )
    op.drop_table("entity_relationships")
