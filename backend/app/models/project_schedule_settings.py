from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectScheduleSettings(Base):
    __tablename__ = "project_schedule_settings"

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    schedule_start_date = Column(String, nullable=False)
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
