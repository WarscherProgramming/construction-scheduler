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


class Submittal(Base):
    __tablename__ = "submittals"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "number",
            name="uq_submittals_project_id_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    number = Column(String, nullable=False)
    specification_section = Column(String, nullable=False)
    title = Column(String, nullable=False)
    responsible_company = Column(String, nullable=True)
    submitted_date = Column(String, nullable=True)
    required_by_date = Column(String, nullable=True)
    reviewed_date = Column(String, nullable=True)
    status = Column(String, nullable=False)
    reviewer = Column(String, nullable=True)
    remarks = Column(Text, nullable=True)

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


class SubmittalNumberSequence(Base):
    __tablename__ = "submittal_number_sequences"

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        primary_key=True,
    )
    last_number = Column(Integer, nullable=False)
