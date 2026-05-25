
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.database import Base


class ChangeOrder(Base):
    __tablename__ = "change_orders"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    date = Column(String, nullable=False)
    co_number = Column(String, nullable=False)
    company = Column(String, nullable=True)
    status = Column(String, nullable=False)

    description = Column(Text, nullable=True)
    amount = Column(String, nullable=True)
    responsible_party = Column(String, nullable=True)