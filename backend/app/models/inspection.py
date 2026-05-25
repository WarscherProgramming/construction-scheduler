
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.database import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    date = Column(String, nullable=False)
    inspection_type = Column(String, nullable=False)
    inspector = Column(String, nullable=True)
    status = Column(String, nullable=False)

    notes = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)