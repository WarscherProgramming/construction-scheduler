from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    true,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_documents_size_bytes_nonnegative",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_documents_version_positive",
        ),
        UniqueConstraint(
            "storage_key",
            name="uq_documents_storage_key",
        ),
        Index(
            "ix_documents_project_listing",
            "project_id",
            "deleted_at",
            "folder_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_documents_version_lineage",
            "parent_document_id",
            "version",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id = Column(
        Integer,
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    extension = Column(String(20), nullable=False)
    mime_type = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    storage_provider = Column(String(50), nullable=False)
    storage_key = Column(String(128), nullable=False)
    storage_bucket = Column(String(255), nullable=True)
    uploaded_by = Column(
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
    version = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    is_current_version = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    document_type = Column(
        String(50),
        nullable=False,
        default="General",
        server_default="General",
    )
    status = Column(
        String(50),
        nullable=False,
        default="Active",
        server_default="Active",
    )
