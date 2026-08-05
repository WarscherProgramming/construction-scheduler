from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectScheduleSettings(Base):
    __tablename__ = "project_schedule_settings"
    __table_args__ = (
        Index(
            "ix_project_schedule_settings_comparison_baseline",
            "comparison_baseline_id",
        ),
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    schedule_start_date = Column(String, nullable=False)
    data_date = Column(String, nullable=False)
    comparison_baseline_id = Column(
        Integer,
        ForeignKey("schedule_baselines.id", ondelete="SET NULL"),
        nullable=True,
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
