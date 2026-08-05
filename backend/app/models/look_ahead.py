from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LookAheadPlan(Base):
    __tablename__ = "look_ahead_plans"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_look_ahead_plans_name_nonblank",
        ),
        CheckConstraint(
            "window_days >= 7 AND window_days <= 42",
            name="ck_look_ahead_plans_window_days",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_look_ahead_plans_status",
        ),
        UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_look_ahead_plans_project_name",
        ),
        Index(
            "ix_look_ahead_plans_project_status_anchor",
            "project_id",
            "status",
            "anchor_date",
            "id",
        ),
        Index(
            "ix_look_ahead_plans_project_created",
            "project_id",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    description = Column(String(2_000), nullable=True)
    anchor_date = Column(String(10), nullable=False)
    window_days = Column(Integer, nullable=False, server_default=text("21"))
    status = Column(
        String(16),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    archived_at = Column(DateTime(timezone=True), nullable=True)


class LookAheadItem(Base):
    __tablename__ = "look_ahead_items"
    __table_args__ = (
        CheckConstraint(
            "readiness_status IN "
            "('unreviewed', 'ready', 'at_risk', 'blocked', "
            "'committed', 'complete')",
            name="ck_look_ahead_items_readiness",
        ),
        CheckConstraint(
            "constraint_category IS NULL OR constraint_category IN "
            "('predecessor_work', 'design_information', 'submittal', "
            "'material', 'labor', 'equipment', 'access', 'inspection', "
            "'permit', 'owner_decision', 'safety', 'weather', 'other')",
            name="ck_look_ahead_items_constraint_category",
        ),
        CheckConstraint(
            "NOT (manually_included AND manually_excluded)",
            name="ck_look_ahead_items_manual_flags",
        ),
        UniqueConstraint(
            "look_ahead_plan_id",
            "task_id",
            name="uq_look_ahead_items_plan_task",
        ),
        Index(
            "ix_look_ahead_items_project_task",
            "project_id",
            "task_id",
        ),
        Index(
            "ix_look_ahead_items_plan_readiness",
            "look_ahead_plan_id",
            "readiness_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    look_ahead_plan_id = Column(
        Integer,
        ForeignKey("look_ahead_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Deliberately not an FK: archived metadata survives task deletion.
    task_id = Column(Integer, nullable=False)
    readiness_status = Column(
        String(16),
        nullable=False,
        default="unreviewed",
        server_default=text("'unreviewed'"),
    )
    blocking_reason = Column(String(2_000), nullable=True)
    constraint_category = Column(String(32), nullable=True)
    constraint_owner = Column(String(255), nullable=True)
    target_resolution_date = Column(String(10), nullable=True)
    commitment_note = Column(String(2_000), nullable=True)
    responsible_company_id = Column(
        Integer,
        ForeignKey("project_companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    manually_included = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    manually_excluded = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    override_reason = Column(String(1_000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
