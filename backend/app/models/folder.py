from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "path",
            name="uq_folders_project_path",
        ),
        Index(
            "ix_folders_project_listing",
            "project_id",
            "deleted_at",
            "path",
            "id",
        ),
        Index(
            "uq_folders_active_root_name",
            "project_id",
            "name",
            unique=True,
            sqlite_where=text(
                "parent_folder_id IS NULL AND deleted_at IS NULL"
            ),
            postgresql_where=text(
                "parent_folder_id IS NULL AND deleted_at IS NULL"
            ),
        ),
        Index(
            "uq_folders_active_child_name",
            "project_id",
            "parent_folder_id",
            "name",
            unique=True,
            sqlite_where=text(
                "parent_folder_id IS NOT NULL AND deleted_at IS NULL"
            ),
            postgresql_where=text(
                "parent_folder_id IS NOT NULL AND deleted_at IS NULL"
            ),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_folder_id = Column(
        Integer,
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(255), nullable=False)
    path = Column(String(2000), nullable=False)
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
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
