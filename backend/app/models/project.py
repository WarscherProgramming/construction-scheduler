
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)