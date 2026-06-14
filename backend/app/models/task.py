
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    duration = Column(Integer)

    predecessor = Column(String, nullable=True)

    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    manual_start_date = Column(String, nullable=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
    )

    order_index = Column(Integer, nullable=True)

    parent_task_id = Column(Integer, nullable=True)
    indent_level = Column(Integer, default=0)
    is_collapsed = Column(Integer, default=0)