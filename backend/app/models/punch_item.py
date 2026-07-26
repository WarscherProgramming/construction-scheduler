from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PunchItem(Base):
    __tablename__ = "punch_items"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "number",
            name="uq_punch_items_project_id_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    number = Column(String, nullable=False)
    location = Column(String, nullable=False)
    trade = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    responsible_company = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    priority = Column(String, nullable=False)
    status = Column(String, nullable=False)
    due_date = Column(String, nullable=True)
    completed_date = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class PunchItemNumberSequence(Base):
    __tablename__ = "punch_item_number_sequences"

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        primary_key=True,
    )
    last_number = Column(Integer, nullable=False)
