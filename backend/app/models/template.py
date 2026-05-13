
from sqlalchemy import Column, Integer, String, ForeignKey
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
    predecessor = Column(String, nullable=True)
    manual_start_date = Column(String, nullable=True)