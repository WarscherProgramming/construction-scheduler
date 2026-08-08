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
    Text,
    UniqueConstraint,
    false,
    func,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PreconstructionExecutionMetric(Base):
    """One measured execution. Written once and never updated.

    This is the single canonical place for *how an execution behaved* —
    timings, query and byte counts, billable units, cost, and reuse. It
    deliberately duplicates nothing: candidate, finding, page, and segment
    counts stay on the records that own them, and this table never restates
    them.
    """

    __tablename__ = "preconstruction_execution_metrics"
    __table_args__ = (
        CheckConstraint(
            "execution_kind IN ('preparation_run', 'analysis_attempt', "
            "'scope_comparison', 'evaluation_run')",
            name="ck_preconstruction_execution_metrics_kind",
        ),
        CheckConstraint(
            "execution_id > 0 AND duration_ms >= 0",
            name="ck_preconstruction_execution_metrics_positive",
        ),
        CheckConstraint(
            "query_count IS NULL OR query_count >= 0",
            name="ck_preconstruction_execution_metrics_query_count",
        ),
        CheckConstraint(
            "response_bytes IS NULL OR response_bytes >= 0",
            name="ck_preconstruction_execution_metrics_response_bytes",
        ),
        CheckConstraint(
            "input_units IS NULL OR input_units >= 0",
            name="ck_preconstruction_execution_metrics_input_units",
        ),
        CheckConstraint(
            "output_units IS NULL OR output_units >= 0",
            name="ck_preconstruction_execution_metrics_output_units",
        ),
        # Cost is either absent (no rate configured) or a non-negative integer
        # in micro-units. It is never a fabricated estimate.
        CheckConstraint(
            "estimated_cost_micros IS NULL OR estimated_cost_micros >= 0",
            name="ck_preconstruction_execution_metrics_cost",
        ),
        CheckConstraint(
            "budget_stop_reason IS NULL OR budget_stop_reason IN "
            "('pair_budget_exceeded', 'assertion_budget_exceeded', "
            "'runtime_budget_exceeded', 'candidate_limit_reached', "
            "'finding_limit_reached')",
            name="ck_preconstruction_execution_metrics_budget_reason",
        ),
        UniqueConstraint(
            "execution_kind",
            "execution_id",
            name="uq_preconstruction_execution_metrics_execution",
        ),
        Index(
            "ix_preconstruction_execution_metrics_project_listing",
            "project_id",
            "execution_kind",
            "recorded_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    execution_kind = Column(String(32), nullable=False)
    # Points at the owning execution record for its kind. Deliberately untyped:
    # the metric never restricts or cascades into the record it measures.
    execution_id = Column(Integer, nullable=False)
    metrics_version = Column(String(100), nullable=False)
    duration_ms = Column(Integer, nullable=False, default=0, server_default="0")
    # Controlled JSON: only phase names from EXECUTION_PHASES, integer
    # milliseconds. No caller-supplied keys are ever stored.
    phase_durations_json = Column(Text, nullable=True)
    query_count = Column(Integer, nullable=True)
    response_bytes = Column(Integer, nullable=True)
    input_units = Column(Integer, nullable=True)
    output_units = Column(Integer, nullable=True)
    estimated_cost_micros = Column(Integer, nullable=True)
    manifest_reused = Column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    budget_stop_reason = Column(String(50), nullable=True)
    recorded_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
