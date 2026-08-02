
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "duration >= 1 AND duration <= 36500",
            name="ck_tasks_duration_range",
        ),
        CheckConstraint(
            "lag_days >= 0 AND lag_days <= 36500",
            name="ck_tasks_lag_days_range",
        ),
        CheckConstraint(
            "dependency_type IN ('FS', 'SS')",
            name="ck_tasks_dependency_type",
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

    @property
    def predecessor(self) -> str | None:
        if self.predecessor_task_id is None:
            return None

        relationship = "SS" if self.dependency_type == "SS" else ""
        lag = f"+{self.lag_days}" if self.lag_days else ""
        return f"{self.predecessor_task_id}{relationship}{lag}"
