from datetime import datetime, timezone

from sqlalchemy import (
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
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleBaseline(Base):
    __tablename__ = "schedule_baselines"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_schedule_baselines_name_nonblank",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_schedule_baselines_status",
        ),
        CheckConstraint(
            "task_count >= 0",
            name="ck_schedule_baselines_task_count_nonnegative",
        ),
        UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_schedule_baselines_project_normalized_name",
        ),
        Index(
            "ix_schedule_baselines_project_captured",
            "project_id",
            "captured_at",
            "id",
        ),
        Index(
            "ix_schedule_baselines_project_status",
            "project_id",
            "status",
            "captured_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    description = Column(String(2_000), nullable=True)
    captured_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    captured_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_start_date = Column(String, nullable=False)
    task_count = Column(Integer, nullable=False)
    status = Column(
        String(16),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class ScheduleBaselineTask(Base):
    __tablename__ = "schedule_baseline_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_id > 0",
            name="ck_schedule_baseline_tasks_task_id_positive",
        ),
        CheckConstraint(
            "duration >= 1 AND duration <= 36500",
            name="ck_schedule_baseline_tasks_duration_range",
        ),
        CheckConstraint(
            "lag_days >= 0 AND lag_days <= 36500",
            name="ck_schedule_baseline_tasks_lag_range",
        ),
        CheckConstraint(
            "dependency_type IN ('FS', 'SS')",
            name="ck_schedule_baseline_tasks_dependency_type",
        ),
        CheckConstraint(
            "order_index IS NULL OR order_index >= 0",
            name="ck_schedule_baseline_tasks_order_nonnegative",
        ),
        CheckConstraint(
            "total_float IS NULL OR total_float >= 0",
            name="ck_schedule_baseline_tasks_float_nonnegative",
        ),
        UniqueConstraint(
            "baseline_id",
            "task_id",
            name="uq_schedule_baseline_tasks_baseline_task",
        ),
        Index(
            "ix_schedule_baseline_tasks_baseline_order",
            "baseline_id",
            "order_index",
            "id",
        ),
        Index(
            "ix_schedule_baseline_tasks_baseline_parent",
            "baseline_id",
            "parent_task_id",
        ),
        Index(
            "ix_schedule_baseline_tasks_baseline_predecessor",
            "baseline_id",
            "predecessor_task_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    baseline_id = Column(
        Integer,
        ForeignKey("schedule_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id = Column(Integer, nullable=False)
    name = Column(String(500), nullable=False)
    order_index = Column(Integer, nullable=True)
    parent_task_id = Column(Integer, nullable=True)
    predecessor_task_id = Column(Integer, nullable=True)
    dependency_type = Column(String(2), nullable=False)
    lag_days = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    manual_start_date = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    is_summary = Column(Boolean, nullable=False)
    was_critical = Column(Boolean, nullable=False)
    total_float = Column(Integer, nullable=True)
    wbs_path = Column(String(10_000), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
