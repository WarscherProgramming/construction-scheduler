
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.database import Base


class NoteDelay(Base):
    __tablename__ = "notes_delays"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    date = Column(String, nullable=False)
    entry_type = Column(String, nullable=False)  # Note or Delay
    company = Column(String, nullable=True)

    description = Column(Text, nullable=False)
    impact = Column(Text, nullable=True)