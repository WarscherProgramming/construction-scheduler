
from sqlalchemy import Column, ForeignKey, Integer, String, text
from app.db.database import Base


class ScheduleTemplate(Base):
    __tablename__ = "schedule_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)


class ScheduleTemplateTask(Base):
    __tablename__ = "schedule_template_tasks"

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
