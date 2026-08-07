from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PreconstructionFindingFollowUp(Base):
    """A human-initiated follow-up raised from an accepted M18.4 finding.

    A follow-up is an intent plus a link. It records that a person decided to
    act and, once they have acted through the existing project workflow, which
    record answers the finding. It never creates, approves, or mutates that
    record, and it carries no review decision of its own: the finding's
    append-only review history remains the sole authority on validity.
    """

    __tablename__ = "preconstruction_finding_follow_ups"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('rfi', 'change_order', 'submittal', "
            "'procurement_action', 'subcontract_clarification', "
            "'internal_follow_up')",
            name="ck_preconstruction_finding_follow_ups_action",
        ),
        CheckConstraint(
            "status IN ('planned', 'linked', 'completed', 'cancelled')",
            name="ck_preconstruction_finding_follow_ups_status",
        ),
        CheckConstraint(
            "target_type IS NULL OR target_type IN ('rfi', 'submittal', "
            "'change_order')",
            name="ck_preconstruction_finding_follow_ups_target_type",
        ),
        # A target is either fully present or fully absent, and a planned
        # follow-up never carries one.
        CheckConstraint(
            "(target_type IS NULL AND target_id IS NULL) OR "
            "(target_type IS NOT NULL AND target_id IS NOT NULL AND target_id > 0)",
            name="ck_preconstruction_finding_follow_ups_target_pair",
        ),
        CheckConstraint(
            "status <> 'planned' OR target_type IS NULL",
            name="ck_preconstruction_finding_follow_ups_planned_has_no_target",
        ),
        CheckConstraint(
            "status <> 'linked' OR target_type IS NOT NULL",
            name="ck_preconstruction_finding_follow_ups_linked_has_target",
        ),
        CheckConstraint(
            "length(trim(draft_title)) > 0",
            name="ck_preconstruction_finding_follow_ups_title_nonblank",
        ),
        CheckConstraint(
            "closure_note IS NULL OR length(closure_note) <= 2000",
            name="ck_preconstruction_finding_follow_ups_note_length",
        ),
        # Closed rows always record who closed them and when.
        CheckConstraint(
            "status IN ('planned', 'linked') OR "
            "(closed_at IS NOT NULL AND closed_by IS NOT NULL)",
            name="ck_preconstruction_finding_follow_ups_closure_identity",
        ),
        # One live follow-up of a given kind per finding, so a double
        # submission can never produce two RFIs for the same finding. Closed
        # rows are excluded, so a genuinely new round of work is still possible
        # after an earlier one is completed or cancelled.
        Index(
            "uq_preconstruction_finding_follow_ups_active_action",
            "finding_id",
            "action_type",
            unique=True,
            sqlite_where=text("status IN ('planned', 'linked')"),
            postgresql_where=text("status IN ('planned', 'linked')"),
        ),
        Index(
            "ix_preconstruction_finding_follow_ups_plan_listing",
            "project_id",
            "comparison_plan_id",
            "status",
            "id",
        ),
        Index(
            "ix_preconstruction_finding_follow_ups_finding_order",
            "project_id",
            "finding_id",
            "id",
        ),
        Index(
            "ix_preconstruction_finding_follow_ups_target",
            "project_id",
            "target_type",
            "target_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    finding_id = Column(
        Integer,
        ForeignKey("preconstruction_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_set_id = Column(
        Integer,
        ForeignKey("preconstruction_review_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    comparison_plan_id = Column(
        Integer,
        ForeignKey("preconstruction_comparison_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The exact human acceptance that authorized this follow-up, pinned so a
    # later review reversal cannot rewrite why the work was raised.
    finding_review_id = Column(
        Integer,
        ForeignKey("preconstruction_finding_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type = Column(String(40), nullable=False)
    status = Column(
        String(16), nullable=False, default="planned", server_default="planned"
    )
    # Resolved through the existing relationship entity resolver. Preconstruction
    # never writes to the referenced table, so this is an untyped reference by
    # design rather than a foreign key.
    target_type = Column(String(32), nullable=True)
    target_id = Column(Integer, nullable=True)
    draft_title = Column(String(200), nullable=False)
    draft_body = Column(String(4000), nullable=False)
    draft_template_version = Column(String(100), nullable=False)
    closure_note = Column(String(2000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        onupdate=utc_now, server_default=func.now()
    )
    linked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    linked_at = Column(DateTime(timezone=True), nullable=True)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
