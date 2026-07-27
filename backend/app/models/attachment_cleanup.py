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


class AttachmentCleanupJob(Base):
    __tablename__ = "attachment_cleanup_jobs"
    __table_args__ = (
        CheckConstraint(
            "operation = 'Delete'",
            name="ck_attachment_cleanup_jobs_operation",
        ),
        CheckConstraint(
            (
                "status IN "
                "('Pending', 'Processing', 'Completed', 'Failed')"
            ),
            name="ck_attachment_cleanup_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_attachment_cleanup_jobs_attempt_nonnegative",
        ),
        Index(
            "ix_attachment_cleanup_jobs_pending",
            "status",
            "next_attempt_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_attachment_cleanup_jobs_lease",
            "status",
            "updated_at",
        ),
        Index(
            "uq_attachment_cleanup_jobs_active_object",
            "storage_provider",
            "storage_key",
            unique=True,
            sqlite_where=text(
                "status IN ('Pending', 'Processing', 'Failed')"
            ),
            postgresql_where=text(
                "status IN ('Pending', 'Processing', 'Failed')"
            ),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(
        Integer,
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id = Column(Integer, nullable=False)
    storage_provider = Column(String(50), nullable=False)
    storage_key = Column(String(64), nullable=False)
    operation = Column(
        String(20),
        nullable=False,
        default="Delete",
        server_default="Delete",
    )
    status = Column(
        String(20),
        nullable=False,
        default="Pending",
        server_default="Pending",
    )
    attempt_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_error = Column(String(500), nullable=True)
    next_attempt_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
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
    completed_at = Column(DateTime(timezone=True), nullable=True)
