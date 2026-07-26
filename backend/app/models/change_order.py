from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChangeOrder(Base):
    __tablename__ = "change_orders"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "co_number",
            name="uq_change_orders_project_id_co_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    date = Column(String, nullable=False)
    co_number = Column(String, nullable=False)
    company = Column(String, nullable=True)
    status = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(String, nullable=True)
    responsible_party = Column(String, nullable=True)

    title = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)
    proposed_amount = Column(Numeric(14, 2), nullable=True)
    approved_amount = Column(Numeric(14, 2), nullable=True)
    schedule_impact_days = Column(Integer, nullable=True)
    requested_date = Column(String, nullable=True)
    submitted_date = Column(String, nullable=True)
    approved_date = Column(String, nullable=True)
    executed_date = Column(String, nullable=True)

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


class ChangeOrderNumberSequence(Base):
    __tablename__ = "change_order_number_sequences"

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        primary_key=True,
    )
    last_number = Column(Integer, nullable=False)
