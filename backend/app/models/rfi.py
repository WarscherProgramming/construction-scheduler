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


class RFI(Base):
    __tablename__ = "rfis"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "number",
            name="uq_rfis_project_id_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    number = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    responsible_company = Column(String, nullable=True)
    submitted_date = Column(String, nullable=False)
    due_date = Column(String, nullable=True)
    response = Column(Text, nullable=True)
    status = Column(String, nullable=False)

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


class RFINumberSequence(Base):
    __tablename__ = "rfi_number_sequences"

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        primary_key=True,
    )
    last_number = Column(Integer, nullable=False)
