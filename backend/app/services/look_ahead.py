from datetime import date, datetime, timedelta, timezone
from math import ceil
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.look_ahead import LookAheadItem, LookAheadPlan
from app.models.project_company import ProjectCompany
from app.models.resource_planning import Crew, EquipmentResource, TaskResourceAssignment
from app.models.task import Task
from app.services.project_schedule_settings import get_project_schedule_settings
from app.services.task_scheduling import schedule_metadata, task_response_rows


MAX_LOOK_AHEAD_PLANS = 100
PlanFilter = Literal["active", "archived", "all"]
TEXT_FIELDS = {
    "blocking_reason",
    "constraint_owner",
    "commitment_note",
    "override_reason",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_plan(
    db: Session,
    project_id: int,
    plan_id: int,
    *,
    for_update: bool = False,
) -> LookAheadPlan:
    query = db.query(LookAheadPlan).filter(
        LookAheadPlan.id == plan_id,
        LookAheadPlan.project_id == project_id,
    )
    if for_update:
        query = query.with_for_update()
    plan = query.first()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Look-ahead plan not found",
        )
    return plan


def _ensure_editable(plan: LookAheadPlan) -> None:
    if plan.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived look-ahead plans are read-only",
        )


def _commit(db: Session, duplicate_detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_detail,
        ) from error
    except Exception:
        db.rollback()
        raise


def create_look_ahead_plan(
    db: Session,
    *,
    project_id: int,
    created_by: int,
    name: str,
    description: str | None,
    anchor_date: str | None,
    window_days: int,
) -> LookAheadPlan:
    settings = get_project_schedule_settings(db, project_id)
    plan = LookAheadPlan(
        project_id=project_id,
        name=name,
        normalized_name=name.casefold(),
        description=description or None,
        anchor_date=anchor_date or settings.data_date,
        window_days=window_days,
        status="active",
        created_by=created_by,
    )
    db.add(plan)
    _commit(db, "A look-ahead plan with this name already exists")
    db.refresh(plan)
    return plan


def list_look_ahead_plans(
    db: Session,
    *,
    project_id: int,
    status_filter: PlanFilter,
    limit: int,
    offset: int,
) -> dict:
    query = db.query(LookAheadPlan).filter(
        LookAheadPlan.project_id == project_id
    )
    if status_filter != "all":
        query = query.filter(LookAheadPlan.status == status_filter)
    total = query.count()
    plans = (
        query.order_by(
            LookAheadPlan.anchor_date.desc(),
            LookAheadPlan.created_at.desc(),
            LookAheadPlan.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"plans": plans, "total": total, "limit": limit, "offset": offset}


def update_look_ahead_plan(
    db: Session,
    *,
    project_id: int,
    plan_id: int,
    values: dict,
) -> LookAheadPlan:
    plan = _get_plan(db, project_id, plan_id, for_update=True)
    _ensure_editable(plan)
    for field, value in values.items():
        if field == "name":
            plan.normalized_name = value.casefold()
        if field == "description":
            value = value or None
        setattr(plan, field, value)
    plan.updated_at = utc_now()
    _commit(db, "A look-ahead plan with this name already exists")
    db.refresh(plan)
    return plan


def archive_look_ahead_plan(
    db: Session,
    *,
    project_id: int,
    plan_id: int,
) -> LookAheadPlan:
    plan = _get_plan(db, project_id, plan_id, for_update=True)
    if plan.status != "archived":
        archived_at = utc_now()
        plan.status = "archived"
        plan.archived_at = archived_at
        plan.updated_at = archived_at
        _commit(db, "Unable to archive look-ahead plan")
        db.refresh(plan)
    return plan


def _build_wbs_map(tasks: list[Task]) -> dict[int, str]:
    wbs: dict[int, str] = {}
    child_counts: dict[str, int] = {}
    for task in tasks:
        parent_wbs = wbs.get(task.parent_task_id)
        key = parent_wbs or "__root__"
        child_counts[key] = child_counts.get(key, 0) + 1
        wbs[task.id] = (
            str(child_counts[key])
            if parent_wbs is None
            else f"{parent_wbs}.{child_counts[key]}"
        )
    return wbs


def _parsed(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _is_automatically_included(
    task: dict,
    *,
    anchor: date,
    window_end: date,
) -> bool:
    start = _parsed(task["start_date"])
    finish = _parsed(task["end_date"])
    actual_start = _parsed(task.get("actual_start_date"))
    completed = task["progress_status"] == "completed"
    if completed and _parsed(task.get("actual_finish_date")) < anchor:
        return False
    if start and finish and start <= window_end and finish >= anchor:
        return True
    if (
        task["progress_status"] == "in_progress"
        and actual_start is not None
        and actual_start <= anchor
    ):
        return True
    return bool(not completed and finish is not None and finish < anchor)


def _week_ranges(anchor: date, window_days: int) -> list[tuple[date, date]]:
    window_end = anchor + timedelta(days=window_days - 1)
    return [
        (
            anchor + timedelta(days=index * 7),
            min(anchor + timedelta(days=(index * 7) + 6), window_end),
        )
        for index in range(ceil(window_days / 7))
    ]


def _metadata_values(metadata: LookAheadItem | None) -> dict:
    return {
        "readiness_status": (
            metadata.readiness_status if metadata else "unreviewed"
        ),
        "blocking_reason": metadata.blocking_reason if metadata else None,
        "constraint_category": (
            metadata.constraint_category if metadata else None
        ),
        "constraint_owner": metadata.constraint_owner if metadata else None,
        "target_resolution_date": (
            metadata.target_resolution_date if metadata else None
        ),
        "commitment_note": metadata.commitment_note if metadata else None,
        "manually_included": bool(metadata and metadata.manually_included),
        "manually_excluded": bool(metadata and metadata.manually_excluded),
        "override_reason": metadata.override_reason if metadata else None,
        "updated_by": metadata.updated_by if metadata else None,
        "updated_at": metadata.updated_at if metadata else None,
    }


def _item_response(
    task: dict | None,
    metadata: LookAheadItem | None,
    company: ProjectCompany | None,
    resource_assignments: list[dict],
    *,
    task_id: int,
    wbs: str | None,
    anchor: date,
    window_end: date,
    section: str,
    week_index: int | None,
) -> dict:
    values = _metadata_values(metadata)
    start = _parsed(task["start_date"]) if task else None
    finish = _parsed(task["end_date"]) if task else None
    overdue = bool(
        task
        and task["progress_status"] != "completed"
        and finish is not None
        and finish < anchor
    )
    target = _parsed(values["target_resolution_date"])
    constraint_due = bool(
        target is not None
        and target <= window_end
        and values["readiness_status"] != "complete"
    )
    spans = bool(
        start
        and finish
        and ((start - anchor).days // 7 != (finish - anchor).days // 7)
    )
    return {
        "task_id": task_id,
        "task_available": task is not None,
        "name": task["name"] if task else None,
        "wbs": wbs,
        "order_index": task["order_index"] if task else None,
        "start_date": task["start_date"] if task else None,
        "end_date": task["end_date"] if task else None,
        "progress_status": task["progress_status"] if task else None,
        "percent_complete": task["percent_complete"] if task else None,
        "is_milestone": bool(task and task["is_milestone"]),
        "is_critical": bool(task and task["is_critical"]),
        "out_of_sequence": bool(task and task["out_of_sequence"]),
        "out_of_sequence_reason": (
            task["out_of_sequence_reason"] if task else None
        ),
        "constraint_type": task["constraint_type"] if task else None,
        "constraint_date": task["constraint_date"] if task else None,
        "predecessor_count": len(task["dependencies"]) if task else 0,
        **values,
        "responsible_company": (
            {"id": company.id, "name": company.name, "trade": company.trade}
            if company
            else None
        ),
        "resource_assignments": resource_assignments,
        "section": section,
        "week_index": week_index,
        "overdue": overdue,
        "starts_this_week": bool(
            start and anchor <= start <= anchor + timedelta(days=6)
        ),
        "continues_from_prior_week": bool(start and start < anchor),
        "spans_multiple_weeks": spans,
        "blocked": values["readiness_status"] == "blocked",
        "constraint_due": constraint_due,
        "commitment_missing": bool(
            task
            and task["progress_status"] != "completed"
            and not values["commitment_note"]
        ),
        "unscheduled": task is not None and not start and not finish,
    }


def get_look_ahead_plan_detail(
    db: Session,
    *,
    project_id: int,
    plan_id: int,
) -> dict:
    plan = _get_plan(db, project_id, plan_id)
    settings = get_project_schedule_settings(db, project_id)
    tasks = (
        db.query(Task).options(joinedload(Task.dependencies))
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )
    metadata_rows = (
        db.query(LookAheadItem)
        .filter(
            LookAheadItem.project_id == project_id,
            LookAheadItem.look_ahead_plan_id == plan.id,
        )
        .all()
    )
    metadata_by_task = {row.task_id: row for row in metadata_rows}
    company_ids = {
        row.responsible_company_id
        for row in metadata_rows
        if row.responsible_company_id is not None
    }
    companies = (
        db.query(ProjectCompany)
        .filter(
            ProjectCompany.project_id == project_id,
            ProjectCompany.id.in_(company_ids),
        )
        .all()
        if company_ids
        else []
    )
    company_by_id = {company.id: company for company in companies}
    assignment_rows = db.query(TaskResourceAssignment).filter(
        TaskResourceAssignment.project_id == project_id
    ).order_by(TaskResourceAssignment.id).all()
    crew_ids = {row.crew_id for row in assignment_rows if row.crew_id is not None}
    equipment_ids = {
        row.equipment_resource_id
        for row in assignment_rows
        if row.equipment_resource_id is not None
    }
    crews = db.query(Crew).filter(Crew.id.in_(crew_ids)).all() if crew_ids else []
    equipment = (
        db.query(EquipmentResource)
        .filter(EquipmentResource.id.in_(equipment_ids))
        .all()
        if equipment_ids
        else []
    )
    crew_by_id = {row.id: row for row in crews}
    equipment_by_id = {row.id: row for row in equipment}
    assignments_by_task: dict[int, list[dict]] = {}
    for assignment in assignment_rows:
        resource = (
            crew_by_id.get(assignment.crew_id)
            if assignment.resource_type == "crew"
            else equipment_by_id.get(assignment.equipment_resource_id)
        )
        if resource is None:
            continue
        assignments_by_task.setdefault(assignment.task_id, []).append(
            {
                "id": assignment.id,
                "resource_type": assignment.resource_type,
                "resource_id": resource.id,
                "name": resource.name,
                "detail": (
                    resource.trade
                    if assignment.resource_type == "crew"
                    else resource.equipment_type
                ),
                "allocation_amount": assignment.allocation_amount,
                "allocation_unit": assignment.allocation_unit,
                "status": resource.status,
            }
        )

    parent_ids = {
        task.parent_task_id for task in tasks if task.parent_task_id is not None
    }
    leaves = [task for task in tasks if task.id not in parent_ids]
    annotated = schedule_metadata(tasks)
    rows_by_id = {
        row["id"]: row
        for row in task_response_rows(tasks, annotated=annotated)
        if row["id"] not in parent_ids
    }
    wbs = _build_wbs_map(tasks)
    anchor = date.fromisoformat(plan.anchor_date)
    window_end = anchor + timedelta(days=plan.window_days - 1)
    ranges = _week_ranges(anchor, plan.window_days)

    carryover: list[dict] = []
    weeks: list[list[dict]] = [[] for _ in ranges]
    manual: list[dict] = []
    excluded: list[dict] = []

    def add_item(task_id: int, task: dict | None, metadata: LookAheadItem | None):
        company = (
            company_by_id.get(metadata.responsible_company_id)
            if metadata
            else None
        )
        manually_included = bool(metadata and metadata.manually_included)
        manually_excluded = bool(metadata and metadata.manually_excluded)
        resource_assignments = assignments_by_task.get(task_id, [])
        if manually_excluded:
            excluded.append(
                _item_response(
                    task,
                    metadata,
                    company,
                    resource_assignments,
                    task_id=task_id,
                    wbs=wbs.get(task_id),
                    anchor=anchor,
                    window_end=window_end,
                    section="excluded",
                    week_index=None,
                )
            )
            return
        if task is None:
            manual.append(
                _item_response(
                    None,
                    metadata,
                    company,
                    resource_assignments,
                    task_id=task_id,
                    wbs=None,
                    anchor=anchor,
                    window_end=window_end,
                    section="manual",
                    week_index=None,
                )
            )
            return
        auto = _is_automatically_included(
            task,
            anchor=anchor,
            window_end=window_end,
        )
        if not auto and not manually_included:
            return
        start = _parsed(task["start_date"])
        incomplete = task["progress_status"] != "completed"
        if start is not None and start < anchor and incomplete:
            section, week_index = "carryover", None
        elif start is not None and anchor <= start <= window_end:
            week_index = min(((start - anchor).days // 7) + 1, len(ranges))
            section = "week"
        else:
            section, week_index = "manual", None
        item = _item_response(
            task,
            metadata,
            company,
            resource_assignments,
            task_id=task_id,
            wbs=wbs.get(task_id),
            anchor=anchor,
            window_end=window_end,
            section=section,
            week_index=week_index,
        )
        if section == "carryover":
            carryover.append(item)
        elif section == "week":
            weeks[week_index - 1].append(item)
        else:
            manual.append(item)

    for task in leaves:
        add_item(task.id, rows_by_id[task.id], metadata_by_task.get(task.id))
    for task_id, metadata in metadata_by_task.items():
        if task_id not in rows_by_id:
            add_item(task_id, None, metadata)

    def sort_key(item: dict):
        return (
            item["start_date"] or "9999-12-31",
            item["order_index"] if item["order_index"] is not None else 2**31,
            item["task_id"],
        )

    carryover.sort(key=sort_key)
    manual.sort(key=sort_key)
    excluded.sort(key=sort_key)
    for group in weeks:
        group.sort(key=sort_key)

    included = carryover + manual + [item for group in weeks for item in group]
    countable = [item for item in included if item["task_available"]]
    readiness = [item["readiness_status"] for item in countable]
    summary = {
        "total_items": len(countable),
        "week_counts": [
            sum(item["task_available"] for item in group) for group in weeks
        ],
        "carryover_count": sum(item["task_available"] for item in carryover),
        "manual_count": sum(item["task_available"] for item in manual),
        "ready_count": readiness.count("ready"),
        "at_risk_count": readiness.count("at_risk"),
        "blocked_count": readiness.count("blocked"),
        "committed_count": readiness.count("committed"),
        "overdue_count": sum(item["overdue"] for item in countable),
        "critical_count": sum(item["is_critical"] for item in countable),
        "out_of_sequence_count": sum(
            item["out_of_sequence"] for item in countable
        ),
        "milestones_count": sum(item["is_milestone"] for item in countable),
        "constraints_due_count": sum(
            item["constraint_due"] for item in countable
        ),
        "unassigned_company_count": sum(
            item["responsible_company"] is None for item in countable
        ),
        "unscheduled_count": sum(item["unscheduled"] for item in countable),
    }
    return {
        "plan": plan,
        "current_data_date": settings.data_date,
        "window_end_date": window_end.isoformat(),
        "summary": summary,
        "carryover_items": carryover,
        "weeks": [
            {
                "week_index": index + 1,
                "start_date": start.isoformat(),
                "end_date": finish.isoformat(),
                "items": weeks[index],
            }
            for index, (start, finish) in enumerate(ranges)
        ],
        "manual_items": manual,
        "excluded_items": excluded,
    }


def update_look_ahead_item(
    db: Session,
    *,
    project_id: int,
    plan_id: int,
    task_id: int,
    updated_by: int,
    values: dict,
) -> dict:
    plan = _get_plan(db, project_id, plan_id, for_update=True)
    _ensure_editable(plan)
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .with_for_update()
        .first()
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule task not found",
        )
    if db.query(Task.id).filter(Task.parent_task_id == task.id).first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Summary tasks cannot be edited as look-ahead items",
        )
    company_id = values.get("responsible_company_id")
    if company_id is not None:
        company = (
            db.query(ProjectCompany.id)
            .filter(
                ProjectCompany.id == company_id,
                ProjectCompany.project_id == project_id,
            )
            .first()
        )
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Responsible company does not belong to this project",
            )
    metadata = (
        db.query(LookAheadItem)
        .filter(
            LookAheadItem.look_ahead_plan_id == plan.id,
            LookAheadItem.task_id == task.id,
        )
        .with_for_update()
        .first()
    )
    if metadata is None:
        metadata = LookAheadItem(
            project_id=project_id,
            look_ahead_plan_id=plan.id,
            task_id=task.id,
            created_by=updated_by,
        )
        db.add(metadata)
    included = values.get("manually_included", metadata.manually_included)
    excluded = values.get("manually_excluded", metadata.manually_excluded)
    if included and excluded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A task cannot be manually included and excluded",
        )
    task_values = {
        "start_date": task.start_date,
        "end_date": task.end_date,
        "actual_start_date": task.actual_start_date,
        "actual_finish_date": task.actual_finish_date,
        "progress_status": task.progress_status,
    }
    if not included and not _is_automatically_included(
        task_values,
        anchor=date.fromisoformat(plan.anchor_date),
        window_end=(
            date.fromisoformat(plan.anchor_date)
            + timedelta(days=plan.window_days - 1)
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Out-of-window tasks must be manually included first",
        )
    for field, value in values.items():
        if field in TEXT_FIELDS:
            value = value or None
        setattr(metadata, field, value)
    metadata.updated_by = updated_by
    metadata.updated_at = utc_now()
    _commit(db, "Look-ahead metadata already exists for this task")
    return get_look_ahead_plan_detail(
        db,
        project_id=project_id,
        plan_id=plan_id,
    )
