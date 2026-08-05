from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, noload

from app.domain.scheduling import workdays_between
from app.models.look_ahead import LookAheadItem, LookAheadPlan
from app.models.schedule_baseline import ScheduleBaseline, ScheduleBaselineTask
from app.models.task import Task
from app.services.project_schedule_settings import get_project_schedule_settings
from app.services.resource_planning import get_resource_health_metrics
from app.services.task_scheduling import schedule_metadata


CRITICAL_FINISH_VARIANCE_WORKDAYS = 10
HEALTH_REASON_LIMIT = 10
ATTENTION_ITEM_LIMIT = 10


def _parsed(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _variance(baseline_value: str | None, current_value: str | None) -> int | None:
    baseline_date = _parsed(baseline_value)
    current_date = _parsed(current_value)
    if baseline_date is None or current_date is None:
        return None
    if current_date >= baseline_date:
        return workdays_between(baseline_date, current_date)
    return -workdays_between(current_date, baseline_date)


def _finish(values) -> str | None:
    parsed = [_parsed(value) for value in values]
    valid = [value for value in parsed if value is not None]
    return max(valid).isoformat() if valid else None


def _baseline(
    db: Session,
    *,
    project_id: int,
    comparison_baseline_id: int | None,
    baseline_id: int | None,
) -> ScheduleBaseline | None:
    if baseline_id is not None:
        row = db.query(ScheduleBaseline).filter(
            ScheduleBaseline.id == baseline_id,
            ScheduleBaseline.project_id == project_id,
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule baseline not found",
            )
        return row
    if comparison_baseline_id is not None:
        row = db.query(ScheduleBaseline).filter(
            ScheduleBaseline.id == comparison_baseline_id,
            ScheduleBaseline.project_id == project_id,
            ScheduleBaseline.status == "active",
        ).first()
        if row is not None:
            return row
    return db.query(ScheduleBaseline).filter(
        ScheduleBaseline.project_id == project_id,
        ScheduleBaseline.status == "active",
    ).order_by(
        ScheduleBaseline.captured_at.desc(),
        ScheduleBaseline.id.desc(),
    ).first()


def _reason(code: str, label: str, severity: str, value: int) -> dict:
    return {"code": code, "label": label, "severity": severity, "value": value}


def _attention(
    *,
    severity: str,
    source: str,
    code: str,
    title: str,
    reason: str,
    task_id: int | None = None,
    due_date: str | None = None,
) -> dict:
    return {
        "severity": severity,
        "source": source,
        "code": code,
        "task_id": task_id,
        "title": (title or "Schedule item")[:500],
        "wbs": None,
        "due_date": due_date,
        "reason": reason[:500],
        "target_page": "schedule",
    }


def get_schedule_health(
    db: Session,
    *,
    project_id: int,
    baseline_id: int | None = None,
) -> dict:
    settings = get_project_schedule_settings(db, project_id)
    data_date = date.fromisoformat(settings.data_date)
    tasks = db.query(Task).options(joinedload(Task.dependencies)).filter(
        Task.project_id == project_id
    ).order_by(Task.order_index, Task.id).all()
    annotated = schedule_metadata(tasks)
    parent_ids = {task.parent_task_id for task in tasks if task.parent_task_id is not None}
    leaves = [
        (task, metadata)
        for task, metadata in zip(tasks, annotated, strict=True)
        if task.id not in parent_ids
    ]
    metadata_by_id = {task.id: metadata for task, metadata in leaves}

    baseline = _baseline(
        db,
        project_id=project_id,
        comparison_baseline_id=settings.comparison_baseline_id,
        baseline_id=baseline_id,
    )
    baseline_tasks = (
        db.query(ScheduleBaselineTask).options(
            noload(ScheduleBaselineTask.dependencies)
        ).filter(
            ScheduleBaselineTask.project_id == project_id,
            ScheduleBaselineTask.baseline_id == baseline.id,
        ).all()
        if baseline is not None
        else []
    )
    baseline_leaves = [row for row in baseline_tasks if not row.is_summary]
    baseline_by_task = {row.task_id: row for row in baseline_leaves}
    current_finish = _finish(task.end_date for task, _ in leaves)
    baseline_finish = _finish(row.end_date for row in baseline_leaves)
    finish_variance = _variance(baseline_finish, current_finish)

    slipped = []
    newly_critical = []
    milestone_variance = []
    for task, metadata in leaves:
        snapshot = baseline_by_task.get(task.id)
        task_variance = _variance(
            snapshot.end_date if snapshot else None,
            task.end_date,
        )
        if task_variance is not None and task_variance > 0:
            slipped.append((task, metadata, task_variance))
            if task.is_milestone:
                milestone_variance.append((task, task_variance))
        if snapshot is not None and metadata.is_critical and not snapshot.was_critical:
            newly_critical.append(task)

    negative_float = [
        (task, metadata)
        for task, metadata in leaves
        if metadata.total_float is not None and metadata.total_float < 0
    ]
    out_of_sequence = [
        (task, metadata) for task, metadata in leaves if metadata.out_of_sequence
    ]
    overdue_incomplete = [
        (task, metadata)
        for task, metadata in leaves
        if metadata.progress_status != "completed"
        and _parsed(task.end_date) is not None
        and _parsed(task.end_date) < data_date
    ]
    constraint_violations = [
        (task, metadata)
        for task, metadata in leaves
        if metadata.constraint_violated
    ]
    mandatory_violations = [
        (task, metadata)
        for task, metadata in constraint_violations
        if task.constraint_type in ("MS", "MF")
    ]
    milestone_window_end = data_date + timedelta(days=20)
    milestones_due = [
        task
        for task, metadata in leaves
        if task.is_milestone
        and metadata.progress_status != "completed"
        and _parsed(task.end_date) is not None
        and data_date <= _parsed(task.end_date) <= milestone_window_end
    ]

    plan = db.query(LookAheadPlan).filter(
        LookAheadPlan.project_id == project_id,
        LookAheadPlan.status == "active",
    ).order_by(LookAheadPlan.anchor_date.desc(), LookAheadPlan.id.desc()).first()
    look_ahead_items = (
        db.query(LookAheadItem).filter(
            LookAheadItem.project_id == project_id,
            LookAheadItem.look_ahead_plan_id == plan.id,
        ).order_by(LookAheadItem.task_id).all()
        if plan is not None
        else []
    )
    blocked_items = [row for row in look_ahead_items if row.readiness_status == "blocked"]
    committed_items = [
        row for row in look_ahead_items if row.readiness_status == "committed"
    ]
    overdue_blockers = [
        row for row in blocked_items
        if _parsed(row.target_resolution_date) is not None
        and _parsed(row.target_resolution_date) < data_date
    ]
    blocked_critical = [
        row for row in blocked_items
        if metadata_by_id.get(row.task_id) is not None
        and metadata_by_id[row.task_id].is_critical
    ]

    resource_health = get_resource_health_metrics(db, project_id=project_id)
    resource_summary = resource_health["summary"]

    metrics = {
        "project_finish_variance_workdays": finish_variance,
        "slipped_tasks": len(slipped),
        "newly_critical_tasks": len(newly_critical),
        "negative_float_tasks": len(negative_float),
        "out_of_sequence_tasks": len(out_of_sequence),
        "overdue_incomplete_tasks": len(overdue_incomplete),
        "constraint_violations": len(constraint_violations),
        "mandatory_constraint_violations": len(mandatory_violations),
        "blocked_look_ahead_items": len(blocked_items),
        "blocked_critical_look_ahead_items": len(blocked_critical),
        "overdue_look_ahead_blockers": len(overdue_blockers),
        "committed_look_ahead_items": len(committed_items),
        "resource_overallocated_days": resource_summary["over_allocated_resource_days"],
        "labor_overallocated_days": resource_summary["labor_overallocated_days"],
        "equipment_overallocated_days": resource_summary["equipment_overallocated_days"],
        "unavailable_resource_conflicts": resource_summary["unavailable_resource_conflicts"],
        "unassigned_executable_tasks": resource_summary["unassigned_executable_tasks"],
        "milestone_variance_count": len(milestone_variance),
        "milestones_due_next_21_days": len(milestones_due),
    }

    critical_reasons = []
    attention_reasons = []
    if finish_variance is not None and finish_variance >= CRITICAL_FINISH_VARIANCE_WORKDAYS:
        critical_reasons.append(_reason(
            "project_finish_critical",
            f"Project finish is {finish_variance} workdays later than baseline.",
            "critical",
            finish_variance,
        ))
    elif finish_variance is not None and finish_variance > 0:
        attention_reasons.append(_reason(
            "project_finish_late",
            f"Project finish is {finish_variance} workdays later than baseline.",
            "attention",
            finish_variance,
        ))
    if baseline is None:
        attention_reasons.append(_reason(
            "baseline_missing",
            "No active comparison baseline is available.",
            "attention",
            1,
        ))
    critical_checks = (
        ("negative_float", "leaf tasks have negative float", len(negative_float)),
        ("mandatory_constraint", "mandatory constraints are not satisfied", len(mandatory_violations)),
        ("unavailable_resource", "resource conflicts occur against zero capacity", metrics["unavailable_resource_conflicts"]),
        ("blocked_critical", "critical look-ahead items are blocked", len(blocked_critical)),
    )
    for code, label, value in critical_checks:
        if value:
            critical_reasons.append(_reason(code, f"{value} {label}.", "critical", value))
    attention_checks = (
        ("slipped_tasks", "leaf tasks are later than baseline", len(slipped)),
        ("newly_critical", "leaf tasks are newly critical", len(newly_critical)),
        ("out_of_sequence", "leaf tasks are out of sequence", len(out_of_sequence)),
        ("overdue_incomplete", "incomplete leaf tasks are past forecast finish", len(overdue_incomplete)),
        ("blocked_look_ahead", "look-ahead items are blocked", len(blocked_items)),
        ("overdue_blockers", "look-ahead blockers are past target date", len(overdue_blockers)),
        ("resource_overallocation", "resource-days are over allocated", metrics["resource_overallocated_days"]),
        ("unassigned_tasks", "executable tasks have no resource assignment", metrics["unassigned_executable_tasks"]),
        ("milestone_variance", "milestones are later than baseline", len(milestone_variance)),
    )
    for code, label, value in attention_checks:
        if value:
            attention_reasons.append(_reason(code, f"{value} {label}.", "attention", value))
    reasons = (critical_reasons + attention_reasons)[:HEALTH_REASON_LIMIT]
    category = "critical" if critical_reasons else "attention" if attention_reasons else "stable"
    summary = {
        "stable": "Schedule health is stable against the configured checks.",
        "attention": "Schedule requires attention.",
        "critical": "Schedule has critical conditions requiring review.",
    }[category]

    attention_items = []
    for task, metadata in mandatory_violations:
        attention_items.append(_attention(
            severity="critical", source="task", code="mandatory_constraint",
            task_id=task.id, title=task.name,
            due_date=task.constraint_date, reason=metadata.constraint_violation_reason or "Mandatory constraint is not satisfied.",
        ))
    for task, metadata in negative_float:
        attention_items.append(_attention(
            severity="critical", source="task", code="negative_float",
            task_id=task.id, title=task.name, due_date=task.end_date,
            reason=f"Task has {metadata.total_float} workdays of total float.",
        ))
    for row in blocked_critical:
        task = next((item for item, _ in leaves if item.id == row.task_id), None)
        attention_items.append(_attention(
            severity="critical", source="look_ahead", code="blocked_critical",
            task_id=row.task_id, title=task.name if task else f"Task {row.task_id}",
            due_date=row.target_resolution_date,
            reason=row.blocking_reason or "Critical look-ahead work is blocked.",
        ))
    for conflict in resource_health["conflicts"]:
        if conflict["status"] != "unavailable":
            continue
        attention_items.append(_attention(
            severity="critical", source="resource", code="unavailable_resource",
            title=conflict["resource"]["name"], due_date=conflict["date"],
            reason=conflict["message"],
        ))
    for task, metadata in overdue_incomplete:
        attention_items.append(_attention(
            severity="attention", source="task", code="overdue_incomplete",
            task_id=task.id, title=task.name, due_date=task.end_date,
            reason="Incomplete task is past its current forecast finish.",
        ))
    for task, metadata, task_variance in slipped:
        if not metadata.is_critical:
            continue
        attention_items.append(_attention(
            severity="attention", source="task", code="slipped_critical",
            task_id=task.id, title=task.name, due_date=task.end_date,
            reason=f"Critical task is {task_variance} workdays later than baseline.",
        ))
    for row in blocked_items:
        if row in blocked_critical:
            continue
        task = next((item for item, _ in leaves if item.id == row.task_id), None)
        attention_items.append(_attention(
            severity="attention", source="look_ahead", code="blocked_look_ahead",
            task_id=row.task_id, title=task.name if task else f"Task {row.task_id}",
            due_date=row.target_resolution_date,
            reason=row.blocking_reason or "Look-ahead work is blocked.",
        ))
    severity_rank = {"critical": 0, "attention": 1}
    attention_items.sort(key=lambda row: (
        severity_rank[row["severity"]],
        row["due_date"] or "9999-12-31",
        row["code"],
        row["task_id"] or 0,
        row["title"],
    ))

    progress_counts = {
        status_value: sum(metadata.progress_status == status_value for _, metadata in leaves)
        for status_value in ("not_started", "in_progress", "completed")
    }
    baseline_response = (
        {
            "id": baseline.id,
            "name": baseline.name,
            "captured_at": baseline.captured_at,
            "project_finish": baseline_finish,
        }
        if baseline is not None
        else None
    )
    return {
        "category": category,
        "summary": summary,
        "reasons": reasons,
        "metrics": metrics,
        "thresholds": {
            "critical_finish_variance_workdays": CRITICAL_FINISH_VARIANCE_WORKDAYS,
            "reason_limit": HEALTH_REASON_LIMIT,
            "attention_item_limit": ATTENTION_ITEM_LIMIT,
        },
        "baseline": baseline_response,
        "data_date": settings.data_date,
        "schedule_start_date": settings.schedule_start_date,
        "executive_summary": {
            "schedule_start_date": settings.schedule_start_date,
            "data_date": settings.data_date,
            "baseline_name": baseline.name if baseline else None,
            "baseline_captured_at": baseline.captured_at if baseline else None,
            "baseline_project_finish": baseline_finish,
            "current_forecast_finish": current_finish,
            "project_finish_variance_workdays": finish_variance,
            "total_leaf_tasks": len(leaves),
            "not_started_tasks": progress_counts["not_started"],
            "in_progress_tasks": progress_counts["in_progress"],
            "completed_tasks": progress_counts["completed"],
            "slipped_tasks": len(slipped),
            "newly_critical_tasks": len(newly_critical),
            "negative_float_tasks": len(negative_float),
            "out_of_sequence_tasks": len(out_of_sequence),
            "milestones_due_next_21_days": len(milestones_due),
            "blocked_look_ahead_items": len(blocked_items),
            "committed_look_ahead_items": len(committed_items),
            "labor_overallocated_days": metrics["labor_overallocated_days"],
            "equipment_overallocated_days": metrics["equipment_overallocated_days"],
            "unassigned_executable_tasks": metrics["unassigned_executable_tasks"],
        },
        "top_attention_items": attention_items[:ATTENTION_ITEM_LIMIT],
    }
