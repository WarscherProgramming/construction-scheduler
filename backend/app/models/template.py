
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class ScheduleTemplate(Base):
    __tablename__ = "schedule_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )


class ScheduleTemplateTask(Base):
    __tablename__ = "schedule_template_tasks"
    __table_args__ = (
        CheckConstraint(
            "duration >= 0 AND duration <= 36500",
            name="ck_schedule_template_tasks_duration_range",
        ),
        CheckConstraint(
            "(is_milestone AND duration = 0) OR "
            "(NOT is_milestone AND duration >= 1)",
            name="ck_schedule_template_tasks_milestone_duration",
        ),
        CheckConstraint(
            "constraint_type IN "
            "('ASAP', 'ALAP', 'SNET', 'SNLT', 'FNET', 'FNLT', 'MS', 'MF')",
            name="ck_schedule_template_tasks_constraint_type",
        ),
        CheckConstraint(
            "(constraint_type IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NULL) OR "
            "(constraint_type NOT IN ('ASAP', 'ALAP') "
            "AND constraint_date IS NOT NULL)",
            name="ck_schedule_template_tasks_constraint_date_required",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    template_id = Column(
        Integer,
        ForeignKey("schedule_templates.id"),
        nullable=False
    )

    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    predecessor_template_task_id = Column(
        Integer,
        ForeignKey("schedule_template_tasks.id", ondelete="SET NULL"),
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
    parent_template_task_id = Column(
        Integer,
        ForeignKey("schedule_template_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_index = Column(Integer, nullable=True)
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

    dependencies = relationship(
        "ScheduleTemplateTaskDependency",
        foreign_keys="ScheduleTemplateTaskDependency.template_task_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ScheduleTemplateTaskDependency.id",
        lazy="selectin",
    )


class ScheduleTemplateTaskDependency(Base):
    __tablename__ = "schedule_template_task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "template_task_id <> predecessor_template_task_id",
            name="ck_template_task_dependencies_not_self",
        ),
        CheckConstraint(
            "dependency_type IN ('FS', 'SS', 'FF', 'SF')",
            name="ck_template_task_dependencies_type",
        ),
        CheckConstraint(
            "lag_days >= -36500 AND lag_days <= 36500",
            name="ck_template_task_dependencies_lag_range",
        ),
        UniqueConstraint(
            "template_task_id",
            "predecessor_template_task_id",
            name="uq_template_task_dependencies_pair",
        ),
        Index(
            "ix_template_task_dependencies_task",
            "template_id",
            "template_task_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("schedule_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_task_id = Column(
        Integer,
        ForeignKey("schedule_template_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    predecessor_template_task_id = Column(
        Integer,
        ForeignKey("schedule_template_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type = Column(String(2), nullable=False)
    lag_days = Column(Integer, nullable=False, default=0, server_default=text("0"))
