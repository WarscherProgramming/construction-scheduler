
from sqlalchemy import Column, ForeignKey, Integer, String, text
from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    duration = Column(Integer)

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
    is_collapsed = Column(Integer, default=0, server_default=text("0"))

    @property
    def predecessor(self) -> str | None:
        if self.predecessor_task_id is None:
            return None

        relationship = "SS" if self.dependency_type == "SS" else ""
        lag = f"+{self.lag_days}" if self.lag_days else ""
        return f"{self.predecessor_task_id}{relationship}{lag}"
