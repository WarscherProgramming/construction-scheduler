
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
    text,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "task_id <> predecessor_task_id",
            name="ck_task_dependencies_not_self",
        ),
        CheckConstraint(
            "dependency_type IN ('FS', 'SS', 'FF', 'SF')",
            name="ck_task_dependencies_type",
        ),
        CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_task_dependencies_lag_range",
        ),
        UniqueConstraint(
            "task_id",
            "predecessor_task_id",
            name="uq_task_dependencies_task_predecessor",
        ),
        Index(
            "ix_task_dependencies_project_task",
            "project_id",
            "task_id",
        ),
        Index(
            "ix_task_dependencies_project_predecessor",
            "project_id",
            "predecessor_task_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    predecessor_task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type = Column(String(2), nullable=False)
    lag_days = Column(Integer, nullable=False, default=0, server_default=text("0"))


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "duration >= 0 AND duration <= 36500",
            name="ck_tasks_duration_range",
        ),
        CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_tasks_lag_days_range",
        ),
        CheckConstraint(
            "dependency_type IN ('FS', 'SS', 'FF', 'SF')",
            name="ck_tasks_dependency_type",
        ),
        CheckConstraint(
            "(is_milestone AND duration = 0) OR "
            "(NOT is_milestone AND duration >= 1)",
            name="ck_tasks_milestone_duration",
        ),
        CheckConstraint(
            "constraint_type IN "
            "('ASAP', 'ALAP', 'SNET', 'SNLT', 'FNET', 'FNLT', 'MS', 'MF')",
            name="ck_tasks_constraint_type",
        ),
        CheckConstraint(
            "(constraint_type IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NULL) OR "
            "(constraint_type NOT IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NOT NULL)",
            name="ck_tasks_constraint_date_required",
        ),
        CheckConstraint(
            "order_index IS NULL OR order_index >= 0",
            name="ck_tasks_order_index_nonnegative",
        ),
        CheckConstraint(
            "is_collapsed IN (0, 1)",
            name="ck_tasks_is_collapsed",
        ),
        CheckConstraint(
            "predecessor_task_id IS NULL OR predecessor_task_id <> id",
            name="ck_tasks_not_own_predecessor",
        ),
        CheckConstraint(
            "parent_task_id IS NULL OR parent_task_id <> id",
            name="ck_tasks_not_own_parent",
        ),
        CheckConstraint(
            "progress_status IN ('not_started', 'in_progress', 'completed')",
            name="ck_tasks_progress_status",
        ),
        CheckConstraint(
            "percent_complete >= 0 AND percent_complete <= 100",
            name="ck_tasks_percent_complete_range",
        ),
        CheckConstraint(
            "remaining_duration >= 0 AND remaining_duration <= 36500",
            name="ck_tasks_remaining_duration_range",
        ),
        CheckConstraint(
            "actual_finish_date IS NULL OR actual_start_date IS NULL "
            "OR actual_finish_date >= actual_start_date",
            name="ck_tasks_actual_date_order",
        ),
        CheckConstraint(
            "(progress_status = 'not_started' "
            "AND percent_complete = 0 "
            "AND actual_start_date IS NULL "
            "AND actual_finish_date IS NULL "
            "AND ((is_milestone AND remaining_duration = 0) "
            "OR (NOT is_milestone AND remaining_duration >= 1))) "
            "OR (progress_status = 'in_progress' "
            "AND NOT is_milestone "
            "AND percent_complete BETWEEN 1 AND 99 "
            "AND actual_start_date IS NOT NULL "
            "AND actual_finish_date IS NULL "
            "AND remaining_duration >= 1) "
            "OR (progress_status = 'completed' "
            "AND percent_complete = 100 "
            "AND actual_start_date IS NOT NULL "
            "AND actual_finish_date IS NOT NULL "
            "AND remaining_duration = 0)",
            name="ck_tasks_progress_state_consistency",
        ),
        Index(
            "ix_tasks_project_order_id",
            "project_id",
            "order_index",
            "id",
        ),
        Index(
            "ix_tasks_project_predecessor",
            "project_id",
            "predecessor_task_id",
        ),
        Index(
            "ix_tasks_project_parent",
            "project_id",
            "parent_task_id",
        ),
        Index(
            "ix_tasks_project_progress_status",
            "project_id",
            "progress_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    duration = Column(Integer, nullable=False)

    predecessor_task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    dependency_type = Column(
        String(2),
        nullable=False,
        default="FS",
        server_default=text("'FS'"),
    )
    lag_days = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    manual_start_date = Column(String, nullable=True)

    is_milestone = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    constraint_type = Column(
        String(4),
        nullable=False,
        default="ASAP",
        server_default=text("'ASAP'"),
    )
    constraint_date = Column(String, nullable=True)

    progress_status = Column(
        String(16),
        nullable=False,
        default="not_started",
        server_default=text("'not_started'"),
    )
    percent_complete = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    actual_start_date = Column(String, nullable=True)
    actual_finish_date = Column(String, nullable=True)
    remaining_duration = Column(
        Integer,
        nullable=False,
        default=lambda context: context.get_current_parameters().get(
            "duration", 1
        ),
    )
    status_updated_at = Column(DateTime(timezone=True), nullable=True)
    status_updated_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
    )

    order_index = Column(Integer, nullable=True)

    parent_task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_collapsed = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    dependencies = relationship(
        TaskDependency,
        foreign_keys=[TaskDependency.task_id],
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=TaskDependency.id,
        lazy="selectin",
    )

    @property
    def predecessor(self) -> str | None:
        dependency = self.dependencies[0] if self.dependencies else None
        predecessor_task_id = (
            dependency.predecessor_task_id
            if dependency is not None
            else self.predecessor_task_id
        )
        if predecessor_task_id is None:
            return None

        dependency_type = (
            dependency.dependency_type if dependency else self.dependency_type
        )
        lag_days = dependency.lag_days if dependency else self.lag_days
        relationship = "" if dependency_type == "FS" else dependency_type
        lag = f"{lag_days:+d}" if lag_days else ""
        return f"{predecessor_task_id}{relationship}{lag}"
