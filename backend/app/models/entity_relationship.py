from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('document', 'drawing_set', 'drawing_sheet', "
            "'drawing_revision', 'drawing_issue', 'rfi', 'submittal', "
            "'punch_item', 'change_order', 'daily_log')",
            name="ck_entity_relationships_source_type",
        ),
        CheckConstraint(
            "target_type IN ('document', 'drawing_set', 'drawing_sheet', "
            "'drawing_revision', 'drawing_issue', 'rfi', 'submittal', "
            "'punch_item', 'change_order', 'daily_log')",
            name="ck_entity_relationships_target_type",
        ),
        CheckConstraint(
            "relationship_type IN ('references', 'responds_to', "
            "'supersedes', 'supports', 'impacts', 'originated_from', "
            "'resolves', 'documents', 'includes', 'associated_with', "
            "'located_on', 'generated_by')",
            name="ck_entity_relationships_relationship_type",
        ),
        CheckConstraint(
            "source_id > 0",
            name="ck_entity_relationships_source_id_positive",
        ),
        CheckConstraint(
            "target_id > 0",
            name="ck_entity_relationships_target_id_positive",
        ),
        CheckConstraint(
            "NOT (source_type = target_type AND source_id = target_id)",
            name="ck_entity_relationships_distinct_entities",
        ),
        Index(
            "uq_entity_relationships_active_pair",
            "project_id",
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship_type",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_entity_relationships_project_source",
            "project_id",
            "source_type",
            "source_id",
            "deleted_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_entity_relationships_project_target",
            "project_id",
            "target_type",
            "target_id",
            "deleted_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_entity_relationships_project_type",
            "project_id",
            "relationship_type",
            "deleted_at",
        ),
        Index(
            "ix_entity_relationships_project_created",
            "project_id",
            "deleted_at",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(32), nullable=False)
    source_id = Column(Integer, nullable=False)
    target_type = Column(String(32), nullable=False)
    target_id = Column(Integer, nullable=False)
    relationship_type = Column(String(32), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
