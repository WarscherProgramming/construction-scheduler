from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_attachments_size_bytes_nonnegative",
        ),
        UniqueConstraint(
            "storage_key",
            name="uq_attachments_storage_key",
        ),
        Index(
            "ix_attachments_parent_listing",
            "project_id",
            "parent_type",
            "parent_id",
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
    parent_type = Column(String(50), nullable=False)
    parent_id = Column(Integer, nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(64), nullable=False)
    storage_provider = Column(String(50), nullable=False)
    mime_type = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    sha256 = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
