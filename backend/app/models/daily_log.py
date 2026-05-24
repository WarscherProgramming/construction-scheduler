
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.database import Base


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    date = Column(String, nullable=False)
    company = Column(String, nullable=False)
    manpower = Column(Integer, nullable=False)

    work_performed = Column(Text, nullable=True)
    delays = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)