from datetime import date, datetime, timezone
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.scheduling import workdays_between
from app.models.project_schedule_settings import ProjectScheduleSettings
from app.models.schedule_baseline import (
    ScheduleBaseline,
    ScheduleBaselineTask,
)
from app.models.task import Task
from app.services.project_schedule_settings import (
    get_project_schedule_settings,
)
from app.services.task_scheduling import (
    annotate_critical_path,
    lock_project_schedule,
    recalculate_schedule,
    schedule_metadata,
)
from app.services.task_validation import validate_schedule_structure


MAX_BASELINE_TASKS = 5_000
BASELINE_LIST_LIMIT = 100
VARIANCE_LIMIT = 200
BaselineFilter = Literal["active", "archived", "all"]


def _ordered_tasks(
    db: Session,
    project_id: int,
    *,
    for_update: bool = False,
) -> list[Task]:
    query = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
    )
    if for_update:
        query = query.with_for_update()
    return query.all()


def _get_baseline(
    db: Session,
    project_id: int,
    baseline_id: int,
) -> ScheduleBaseline:
    baseline = (
        db.query(ScheduleBaseline)
        .filter(
            ScheduleBaseline.id == baseline_id,
            ScheduleBaseline.project_id == project_id,
        )
        .first()
    )
    if baseline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule baseline not found",
        )
    return baseline


def _build_wbs_map(tasks: list[object]) -> dict[int, str]:
    wbs: dict[int, str] = {}
    child_counts: dict[str, int] = {}

    for task in tasks:
        parent_id = getattr(task, "parent_task_id", None)
        parent_wbs = wbs.get(parent_id) if parent_id is not None else None
        count_key = parent_wbs or "__root__"
        count = child_counts.get(count_key, 0) + 1
        child_counts[count_key] = count
        wbs[task.task_id if hasattr(task, "task_id") else task.id] = (
            str(count) if parent_wbs is None else f"{parent_wbs}.{count}"
        )

    return wbs


def capture_schedule_baseline(
    db: Session,
    *,
    project_id: int,
    captured_by: int,
    name: str,
    description: str | None,
) -> tuple[ScheduleBaseline, int]:
    normalized_name = name.casefold()

    try:
        lock_project_schedule(db, project_id)
        settings = get_project_schedule_settings(db, project_id)
        duplicate = (
            db.query(ScheduleBaseline.id)
            .filter(
                ScheduleBaseline.project_id == project_id,
                ScheduleBaseline.normalized_name == normalized_name,
            )
            .first()
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A schedule baseline with this name already exists",
            )

        tasks = _ordered_tasks(db, project_id, for_update=True)
        if len(tasks) > MAX_BASELINE_TASKS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"A baseline cannot contain more than "
                    f"{MAX_BASELINE_TASKS} tasks"
                ),
            )

        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=date.fromisoformat(settings.schedule_start_date),
            data_date=date.fromisoformat(settings.data_date),
        )
        annotate_critical_path(tasks)

        captured_at = datetime.now(timezone.utc)
        baseline = ScheduleBaseline(
            project_id=project_id,
            name=name,
            normalized_name=normalized_name,
            description=description or None,
            captured_at=captured_at,
            captured_by=captured_by,
            schedule_start_date=settings.schedule_start_date,
            task_count=len(tasks),
            status="active",
            created_at=captured_at,
        )
        db.add(baseline)
        db.flush()

        parent_ids = {
            task.parent_task_id
            for task in tasks
            if task.parent_task_id is not None
        }
        wbs_map = _build_wbs_map(tasks)
        snapshots = [
            ScheduleBaselineTask(
                baseline_id=baseline.id,
                project_id=project_id,
                task_id=task.id,
                name=task.name or "Untitled task",
                order_index=task.order_index,
                parent_task_id=task.parent_task_id,
                predecessor_task_id=task.predecessor_task_id,
                dependency_type=task.dependency_type,
                lag_days=task.lag_days,
                duration=task.duration,
                manual_start_date=task.manual_start_date,
                start_date=task.start_date,
                end_date=task.end_date,
                is_summary=task.id in parent_ids,
                was_critical=bool(task.is_critical),
                total_float=task.total_float,
                wbs_path=wbs_map[task.id],
                created_at=captured_at,
            )
            for task in tasks
        ]
        db.add_all(snapshots)
        settings.comparison_baseline_id = baseline.id
        db.flush()
        db.commit()
        db.refresh(baseline)
        return baseline, baseline.id
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A schedule baseline with this name already exists",
        ) from error
    except Exception:
        db.rollback()
        raise


def list_schedule_baselines(
    db: Session,
    *,
    project_id: int,
    status_filter: BaselineFilter,
    limit: int,
    offset: int,
) -> dict:
    query = db.query(ScheduleBaseline).filter(
        ScheduleBaseline.project_id == project_id
    )
    if status_filter != "all":
        query = query.filter(ScheduleBaseline.status == status_filter)

    total = query.count()
    baselines = (
        query.order_by(
            ScheduleBaseline.captured_at.desc(),
            ScheduleBaseline.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    settings = get_project_schedule_settings(db, project_id)
    return {
        "baselines": baselines,
        "comparison_baseline_id": settings.comparison_baseline_id,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_schedule_baseline_detail(
    db: Session,
    *,
    project_id: int,
    baseline_id: int,
    limit: int,
    offset: int,
) -> dict:
    baseline = _get_baseline(db, project_id, baseline_id)
    query = db.query(ScheduleBaselineTask).filter(
        ScheduleBaselineTask.baseline_id == baseline.id,
        ScheduleBaselineTask.project_id == project_id,
    )
    total = query.count()
    tasks = (
        query.order_by(
            ScheduleBaselineTask.order_index,
            ScheduleBaselineTask.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "baseline": baseline,
        "tasks": tasks,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def archive_schedule_baseline(
    db: Session,
    *,
    project_id: int,
    baseline_id: int,
) -> tuple[ScheduleBaseline, int | None]:
    try:
        lock_project_schedule(db, project_id)
        baseline = _get_baseline(db, project_id, baseline_id)
        settings = get_project_schedule_settings(db, project_id)

        if baseline.status != "archived":
            baseline.status = "archived"
            baseline.archived_at = datetime.now(timezone.utc)
        if settings.comparison_baseline_id == baseline.id:
            settings.comparison_baseline_id = None

        db.commit()
        db.refresh(baseline)
        return baseline, settings.comparison_baseline_id
    except Exception:
        db.rollback()
        raise


def select_comparison_baseline(
    db: Session,
    *,
    project_id: int,
    baseline_id: int | None,
) -> ProjectScheduleSettings:
    try:
        lock_project_schedule(db, project_id)
        settings = get_project_schedule_settings(db, project_id)
        if baseline_id is not None:
            baseline = _get_baseline(db, project_id, baseline_id)
            if baseline.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Archived baselines cannot be the default comparison"
                    ),
                )

        settings.comparison_baseline_id = baseline_id
        db.commit()
        db.refresh(settings)
        return settings
    except Exception:
        db.rollback()
        raise


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _workday_variance(
    baseline_value: str | None,
    current_value: str | None,
) -> int | None:
    baseline_date = _parse_date(baseline_value)
    current_date = _parse_date(current_value)
    if baseline_date is None or current_date is None:
        return None
    if current_date >= baseline_date:
        return workdays_between(baseline_date, current_date)
    return -workdays_between(current_date, baseline_date)


def _critical_change(
    baseline_task: ScheduleBaselineTask | None,
    current_task: Task | None,
    *,
    current_is_summary: bool,
    current_is_critical: bool,
) -> str | None:
    if (
        baseline_task is None
        or current_task is None
        or baseline_task.is_summary
        or current_is_summary
    ):
        return None
    before = bool(baseline_task.was_critical)
    after = current_is_critical
    if before and after:
        return "remained_critical"
    if before:
        return "no_longer_critical"
    if after:
        return "newly_critical"
    return "remained_noncritical"


def _comparison_status(
    baseline_task: ScheduleBaselineTask | None,
    current_task: Task | None,
) -> tuple[str, int | None]:
    if baseline_task is None:
        return "added", None
    if current_task is None:
        return "removed", None
    if baseline_task.end_date is None or current_task.end_date is None:
        return "unscheduled", None
    try:
        finish_variance = _workday_variance(
            baseline_task.end_date,
            current_task.end_date,
        )
    except ValueError:
        return "incomparable", None
    if finish_variance is None:
        return "unscheduled", None
    if finish_variance > 0:
        return "slipped", finish_variance
    if finish_variance < 0:
        return "improved", finish_variance
    return "unchanged", 0


def _comparison_row(
    task_id: int,
    baseline_task: ScheduleBaselineTask | None,
    current_task: Task | None,
    current_metadata,
    *,
    baseline_wbs: dict[int, str],
    current_wbs: dict[int, str],
    current_summary_ids: set[int],
) -> dict:
    current_is_summary = bool(
        current_task and current_task.id in current_summary_ids
    )
    comparison_status, finish_variance = _comparison_status(
        baseline_task,
        current_task,
    )

    start_variance = None
    if baseline_task is not None and current_task is not None:
        try:
            start_variance = _workday_variance(
                baseline_task.start_date,
                current_task.start_date,
            )
        except ValueError:
            start_variance = None

    baseline_float = baseline_task.total_float if baseline_task else None
    current_float = current_metadata.total_float if current_metadata else None
    float_variance = (
        current_float - baseline_float
        if current_float is not None and baseline_float is not None
        else None
    )
    baseline_duration = baseline_task.duration if baseline_task else None
    current_duration = current_task.duration if current_task else None
    duration_variance = (
        current_duration - baseline_duration
        if current_duration is not None and baseline_duration is not None
        else None
    )
    matched = baseline_task is not None and current_task is not None
    baseline_code = baseline_wbs.get(task_id)
    current_code = current_wbs.get(task_id)

    return {
        "task_id": task_id,
        "baseline_task_id": baseline_task.id if baseline_task else None,
        "name": (
            current_task.name
            if current_task is not None
            else baseline_task.name
        ) or "Untitled task",
        "wbs": current_code or baseline_code or "-",
        "baseline_wbs": baseline_code,
        "current_wbs": current_code,
        "is_summary": bool(
            current_is_summary
            or (baseline_task and baseline_task.is_summary)
        ),
        "current_start_date": (
            current_task.start_date if current_task else None
        ),
        "current_end_date": current_task.end_date if current_task else None,
        "baseline_start_date": (
            baseline_task.start_date if baseline_task else None
        ),
        "baseline_end_date": baseline_task.end_date if baseline_task else None,
        "start_variance_workdays": start_variance if matched else None,
        "finish_variance_workdays": finish_variance,
        "current_duration": current_duration,
        "baseline_duration": baseline_duration,
        "duration_variance_days": duration_variance,
        "current_total_float": current_float,
        "baseline_total_float": baseline_float,
        "float_variance_workdays": float_variance,
        "current_critical": (
            bool(current_metadata.is_critical) if current_metadata else None
        ),
        "baseline_critical": (
            bool(baseline_task.was_critical) if baseline_task else None
        ),
        "critical_change": _critical_change(
            baseline_task,
            current_task,
            current_is_summary=current_is_summary,
            current_is_critical=bool(
                current_metadata and current_metadata.is_critical
            ),
        ),
        "comparison_status": comparison_status,
        "hierarchy_changed": bool(
            matched
            and baseline_task.parent_task_id != current_task.parent_task_id
        ),
        "dependency_changed": bool(
            matched
            and (
                baseline_task.predecessor_task_id
                != current_task.predecessor_task_id
                or baseline_task.dependency_type
                != current_task.dependency_type
                or baseline_task.lag_days != current_task.lag_days
            )
        ),
        "duration_changed": bool(matched and duration_variance != 0),
        "manual_start_changed": bool(
            matched
            and baseline_task.manual_start_date
            != current_task.manual_start_date
        ),
        "order_changed": bool(
            matched
            and (
                baseline_task.order_index != current_task.order_index
                or baseline_code != current_code
            )
        ),
        "progress_status": (
            current_metadata.progress_status if current_metadata else None
        ),
        "percent_complete": (
            current_metadata.percent_complete if current_metadata else None
        ),
        "actual_start_date": (
            current_metadata.actual_start_date if current_metadata else None
        ),
        "actual_finish_date": (
            current_metadata.actual_finish_date if current_metadata else None
        ),
        "remaining_duration": (
            current_metadata.remaining_duration if current_metadata else None
        ),
        "out_of_sequence": bool(
            current_metadata and current_metadata.out_of_sequence
        ),
        "out_of_sequence_reason": (
            current_metadata.out_of_sequence_reason
            if current_metadata
            else None
        ),
    }


def _valid_finish(values: list[str | None]) -> str | None:
    valid: list[str] = []
    for value in values:
        try:
            parsed = _parse_date(value)
        except ValueError:
            continue
        if parsed is not None:
            valid.append(parsed.isoformat())
    return max(valid) if valid else None


def _variance_summary(
    baseline: ScheduleBaseline,
    settings: ProjectScheduleSettings,
    rows: list[dict],
    baseline_tasks: list[ScheduleBaselineTask],
    current_tasks: list[Task],
    current_summary_ids: set[int],
    current_metadata_map: dict,
) -> dict:
    leaf_rows = [row for row in rows if not row["is_summary"]]
    baseline_leaves = [task for task in baseline_tasks if not task.is_summary]
    current_leaves = [
        task for task in current_tasks if task.id not in current_summary_ids
    ]
    baseline_finish = _valid_finish(
        [task.end_date for task in baseline_leaves]
    )
    current_finish = _valid_finish([task.end_date for task in current_leaves])
    try:
        project_finish_variance = _workday_variance(
            baseline_finish,
            current_finish,
        )
    except ValueError:
        project_finish_variance = None

    status_counts = {
        key: sum(row["comparison_status"] == key for row in leaf_rows)
        for key in (
            "slipped",
            "improved",
            "unchanged",
            "added",
            "removed",
            "unscheduled",
            "incomparable",
        )
    }
    return {
        "baseline_id": baseline.id,
        "baseline_name": baseline.name,
        "captured_at": baseline.captured_at,
        "baseline_schedule_start_date": baseline.schedule_start_date,
        "current_schedule_start_date": settings.schedule_start_date,
        "current_data_date": settings.data_date,
        "baseline_task_count": baseline.task_count,
        "current_task_count": len(current_tasks),
        "baseline_leaf_task_count": len(baseline_leaves),
        "current_leaf_task_count": len(current_leaves),
        "slipped_count": status_counts["slipped"],
        "improved_count": status_counts["improved"],
        "unchanged_count": status_counts["unchanged"],
        "added_count": status_counts["added"],
        "removed_count": status_counts["removed"],
        "unscheduled_count": status_counts["unscheduled"],
        "incomparable_count": status_counts["incomparable"],
        "baseline_project_finish": baseline_finish,
        "current_project_finish": current_finish,
        "project_finish_variance_workdays": project_finish_variance,
        "baseline_critical_count": sum(
            bool(task.was_critical) for task in baseline_leaves
        ),
        "current_critical_count": sum(
            bool(current_metadata_map.get(task.id).is_critical)
            for task in current_leaves
            if current_metadata_map.get(task.id) is not None
        ),
        "newly_critical_count": sum(
            row["critical_change"] == "newly_critical" for row in leaf_rows
        ),
        "no_longer_critical_count": sum(
            row["critical_change"] == "no_longer_critical"
            for row in leaf_rows
        ),
        "not_started_count": sum(
            current_metadata_map.get(task.id) is not None
            and current_metadata_map[task.id].progress_status == "not_started"
            for task in current_leaves
        ),
        "in_progress_count": sum(
            current_metadata_map.get(task.id) is not None
            and current_metadata_map[task.id].progress_status == "in_progress"
            for task in current_leaves
        ),
        "completed_count": sum(
            current_metadata_map.get(task.id) is not None
            and current_metadata_map[task.id].progress_status == "completed"
            for task in current_leaves
        ),
        "out_of_sequence_count": sum(
            current_metadata_map.get(task.id) is not None
            and current_metadata_map[task.id].out_of_sequence
            for task in current_leaves
        ),
    }


def _wbs_sort_key(value: str) -> tuple:
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError:
        return (2_147_483_647, value)


def _sort_rows(rows: list[dict], sort: str, order: str) -> list[dict]:
    fields = {
        "wbs": lambda row: _wbs_sort_key(row["wbs"]),
        "name": lambda row: row["name"].casefold(),
        "baseline_start": lambda row: row["baseline_start_date"],
        "current_start": lambda row: row["current_start_date"],
        "baseline_finish": lambda row: row["baseline_end_date"],
        "current_finish": lambda row: row["current_end_date"],
        "start_variance": lambda row: row["start_variance_workdays"],
        "finish_variance": lambda row: row["finish_variance_workdays"],
        "duration_variance": lambda row: row["duration_variance_days"],
        "status": lambda row: row["comparison_status"],
        "critical_change": lambda row: row["critical_change"],
    }
    key = fields[sort]
    present = [row for row in rows if key(row) is not None]
    missing = [row for row in rows if key(row) is None]
    present.sort(
        key=lambda row: (key(row), row["task_id"]),
        reverse=order == "desc",
    )
    return present + missing


def get_schedule_variance(
    db: Session,
    *,
    project_id: int,
    baseline_id: int | None,
    include_summaries: bool,
    status_filter: str | None,
    critical_change_filter: str | None,
    search: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> dict:
    settings = get_project_schedule_settings(db, project_id)
    if baseline_id is not None:
        baseline = _get_baseline(db, project_id, baseline_id)
    elif settings.comparison_baseline_id is not None:
        baseline = (
            db.query(ScheduleBaseline)
            .filter(
                ScheduleBaseline.id == settings.comparison_baseline_id,
                ScheduleBaseline.project_id == project_id,
                ScheduleBaseline.status == "active",
            )
            .first()
        )
    else:
        baseline = None

    if baseline is None and baseline_id is None:
        baseline = (
            db.query(ScheduleBaseline)
            .filter(
                ScheduleBaseline.project_id == project_id,
                ScheduleBaseline.status == "active",
            )
            .order_by(
                ScheduleBaseline.captured_at.desc(),
                ScheduleBaseline.id.desc(),
            )
            .first()
        )

    if baseline is None:
        return {
            "baseline": None,
            "summary": None,
            "tasks": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    current_tasks = _ordered_tasks(db, project_id)
    if len(current_tasks) > MAX_BASELINE_TASKS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Schedule variance is limited to {MAX_BASELINE_TASKS} "
                "current tasks"
            ),
        )
    valid_critical_tasks: list[Task] = []
    for task in current_tasks:
        try:
            _parse_date(task.start_date)
            _parse_date(task.end_date)
            _parse_date(task.actual_start_date)
            _parse_date(task.actual_finish_date)
        except ValueError:
            task.is_critical = False
            task.total_float = None
        else:
            valid_critical_tasks.append(task)
    current_metadata = schedule_metadata(valid_critical_tasks)
    current_metadata_map = {
        task.id: metadata
        for task, metadata in zip(
            valid_critical_tasks,
            current_metadata,
            strict=True,
        )
    }
    for task, metadata in zip(
        valid_critical_tasks,
        current_metadata,
        strict=True,
    ):
        task.is_critical = metadata.is_critical
        task.total_float = metadata.total_float
    baseline_tasks = (
        db.query(ScheduleBaselineTask)
        .filter(
            ScheduleBaselineTask.baseline_id == baseline.id,
            ScheduleBaselineTask.project_id == project_id,
        )
        .order_by(
            ScheduleBaselineTask.order_index,
            ScheduleBaselineTask.id,
        )
        .all()
    )

    current_map = {task.id: task for task in current_tasks}
    baseline_map = {task.task_id: task for task in baseline_tasks}
    current_wbs = _build_wbs_map(current_tasks)
    baseline_wbs = {
        task.task_id: task.wbs_path for task in baseline_tasks
    }
    current_summary_ids = {
        task.parent_task_id
        for task in current_tasks
        if task.parent_task_id is not None
    }
    task_ids = [task.id for task in current_tasks]
    task_ids.extend(
        task.task_id
        for task in baseline_tasks
        if task.task_id not in current_map
    )
    all_rows = [
        _comparison_row(
            task_id,
            baseline_map.get(task_id),
            current_map.get(task_id),
            current_metadata_map.get(task_id),
            baseline_wbs=baseline_wbs,
            current_wbs=current_wbs,
            current_summary_ids=current_summary_ids,
        )
        for task_id in task_ids
    ]
    summary = _variance_summary(
        baseline,
        settings,
        all_rows,
        baseline_tasks,
        current_tasks,
        current_summary_ids,
        current_metadata_map,
    )

    rows = all_rows
    if not include_summaries:
        rows = [row for row in rows if not row["is_summary"]]
    if status_filter:
        rows = [
            row for row in rows if row["comparison_status"] == status_filter
        ]
    if critical_change_filter:
        rows = [
            row
            for row in rows
            if row["critical_change"] == critical_change_filter
        ]
    if search:
        normalized_search = search.casefold()
        rows = [
            row
            for row in rows
            if normalized_search in row["name"].casefold()
            or normalized_search in row["wbs"].casefold()
        ]

    rows = _sort_rows(rows, sort, order)
    total = len(rows)
    return {
        "baseline": baseline,
        "summary": summary,
        "tasks": rows[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
