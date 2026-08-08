"""Persistence and reads for preconstruction execution metrics.

One canonical place for *how an execution behaved*. It records timings, query
and byte counts, billable units, cost, reuse, and budget stops. It deliberately
restates nothing: candidate, finding, page, and segment counts stay on the
records that own them.

Metric rows are written once and never updated, so a historical execution's
measured cost can never be rewritten. Recording is best-effort: a metrics
failure must never fail or roll back the work being measured.
"""

from datetime import datetime, timezone
import json
import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import PreconstructionExecutionConfig
from app.models.preconstruction_metrics import PreconstructionExecutionMetric
from app.preconstruction.execution import (
    BUDGET_STOP_REASONS,
    EXECUTION_KINDS,
    ExecutionMetrics,
    estimate_cost_micros,
    format_cost_micros,
)


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def record_execution_metrics(
    db: Session,
    project_id: int,
    metrics: ExecutionMetrics,
    config: PreconstructionExecutionConfig,
    *,
    commit: bool = False,
) -> PreconstructionExecutionMetric | None:
    """Append one metric row inside the caller's transaction.

    Returns ``None`` when metrics are disabled or when the row could not be
    written. Measurement never breaks the thing being measured: a duplicate or
    database error is logged with identifiers only and swallowed.
    """
    if not config.metrics_enabled:
        return None
    if metrics.execution_kind not in EXECUTION_KINDS:
        return None

    # Metric rows are written once per execution. A reused finding set already
    # carries its own measurement, so a second row is neither written nor
    # treated as an error.
    existing = get_execution_metric(
        db, project_id, metrics.execution_kind, metrics.execution_id
    )
    if existing is not None:
        return existing

    cost = metrics.estimated_cost_micros
    if cost is None:
        cost = estimate_cost_micros(
            metrics.input_units,
            metrics.output_units,
            config.cost_input_micros_per_unit,
            config.cost_output_micros_per_unit,
        )

    row = PreconstructionExecutionMetric(
        project_id=project_id,
        execution_kind=metrics.execution_kind,
        execution_id=metrics.execution_id,
        metrics_version=config.metrics_version,
        duration_ms=max(0, metrics.duration_ms),
        phase_durations_json=(
            _canonical(metrics.phase_durations) if metrics.phase_durations else None
        ),
        query_count=metrics.query_count,
        response_bytes=metrics.response_bytes,
        input_units=metrics.input_units,
        output_units=metrics.output_units,
        estimated_cost_micros=cost,
        manifest_reused=metrics.manifest_reused,
        budget_stop_reason=metrics.budget_stop_reason,
        recorded_at=utc_now(),
    )
    try:
        # A savepoint keeps a metrics failure from discarding the caller's
        # work: measurement must never roll back the thing being measured.
        with db.begin_nested():
            db.add(row)
            db.flush()
        if commit:
            db.commit()
            db.refresh(row)
    except SQLAlchemyError:
        logger.warning(
            "preconstruction execution metrics not recorded kind=%s execution_id=%s",
            metrics.execution_kind,
            metrics.execution_id,
        )
        return None
    return row


def metric_payload(row: PreconstructionExecutionMetric) -> dict:
    """Safe response shape. Never carries text, prompts, or provider output."""
    return {
        "id": row.id,
        "execution_kind": row.execution_kind,
        "execution_kind_label": EXECUTION_KINDS.get(
            row.execution_kind, row.execution_kind
        ),
        "execution_id": row.execution_id,
        "metrics_version": row.metrics_version,
        "duration_ms": row.duration_ms,
        "phase_durations": (
            json.loads(row.phase_durations_json) if row.phase_durations_json else {}
        ),
        "query_count": row.query_count,
        "response_bytes": row.response_bytes,
        "input_units": row.input_units,
        "output_units": row.output_units,
        "estimated_cost_micros": row.estimated_cost_micros,
        "estimated_cost_display": format_cost_micros(row.estimated_cost_micros),
        "cost_rate_configured": row.estimated_cost_micros is not None,
        "manifest_reused": row.manifest_reused,
        "budget_stop_reason": row.budget_stop_reason,
        "budget_stop_label": (
            BUDGET_STOP_REASONS.get(row.budget_stop_reason)
            if row.budget_stop_reason
            else None
        ),
        "recorded_at": row.recorded_at,
    }


def get_execution_metric(
    db: Session, project_id: int, execution_kind: str, execution_id: int
) -> PreconstructionExecutionMetric | None:
    return (
        db.query(PreconstructionExecutionMetric)
        .filter(
            PreconstructionExecutionMetric.project_id == project_id,
            PreconstructionExecutionMetric.execution_kind == execution_kind,
            PreconstructionExecutionMetric.execution_id == execution_id,
        )
        .first()
    )


def metrics_for_executions(
    db: Session, project_id: int, execution_kind: str, execution_ids: list[int]
) -> dict[int, PreconstructionExecutionMetric]:
    """One batched lookup for a page of executions. No per-row query."""
    if not execution_ids:
        return {}
    rows = (
        db.query(PreconstructionExecutionMetric)
        .filter(
            PreconstructionExecutionMetric.project_id == project_id,
            PreconstructionExecutionMetric.execution_kind == execution_kind,
            PreconstructionExecutionMetric.execution_id.in_(execution_ids),
        )
        .all()
    )
    return {row.execution_id: row for row in rows}


def list_execution_metrics(
    db: Session,
    project_id: int,
    *,
    limit: int,
    offset: int,
    execution_kind: str | None = None,
) -> tuple[list[PreconstructionExecutionMetric], int]:
    query = db.query(PreconstructionExecutionMetric).filter(
        PreconstructionExecutionMetric.project_id == project_id
    )
    if execution_kind:
        query = query.filter(
            PreconstructionExecutionMetric.execution_kind == execution_kind
        )
    total = query.with_entities(
        func.count(PreconstructionExecutionMetric.id)
    ).scalar()
    items = (
        query.order_by(
            PreconstructionExecutionMetric.recorded_at.desc(),
            PreconstructionExecutionMetric.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def execution_metrics_summary(
    db: Session, project_id: int, execution_kind: str | None = None
) -> dict:
    """Aggregate roll-up in one grouped query. Bounded and text-free."""
    query = db.query(
        PreconstructionExecutionMetric.execution_kind,
        func.count(PreconstructionExecutionMetric.id),
        func.sum(PreconstructionExecutionMetric.duration_ms),
        func.max(PreconstructionExecutionMetric.duration_ms),
        func.sum(PreconstructionExecutionMetric.input_units),
        func.sum(PreconstructionExecutionMetric.output_units),
        func.sum(PreconstructionExecutionMetric.estimated_cost_micros),
    ).filter(PreconstructionExecutionMetric.project_id == project_id)
    if execution_kind:
        query = query.filter(
            PreconstructionExecutionMetric.execution_kind == execution_kind
        )
    rows = query.group_by(PreconstructionExecutionMetric.execution_kind).all()

    by_kind = {}
    total_executions = 0
    total_duration = 0
    total_cost: int | None = None
    for kind, count, duration_sum, duration_max, inputs, outputs, cost in rows:
        total_executions += count or 0
        total_duration += int(duration_sum or 0)
        if cost is not None:
            total_cost = (total_cost or 0) + int(cost)
        by_kind[kind] = {
            "execution_kind": kind,
            "execution_kind_label": EXECUTION_KINDS.get(kind, kind),
            "count": count or 0,
            "total_duration_ms": int(duration_sum or 0),
            "max_duration_ms": int(duration_max or 0),
            "average_duration_ms": int((duration_sum or 0) / count) if count else 0,
            "input_units": int(inputs) if inputs is not None else None,
            "output_units": int(outputs) if outputs is not None else None,
            "estimated_cost_micros": int(cost) if cost is not None else None,
        }
    return {
        "total_executions": total_executions,
        "total_duration_ms": total_duration,
        "estimated_cost_micros": total_cost,
        "estimated_cost_display": format_cost_micros(total_cost),
        "cost_rate_configured": total_cost is not None,
        "by_kind": [by_kind[key] for key in sorted(by_kind)],
    }
