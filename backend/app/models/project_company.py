
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base


class ProjectCompany(Base):
    __tablename__ = "project_companies"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String, nullable=False)
    trade = Column(String, nullable=True)