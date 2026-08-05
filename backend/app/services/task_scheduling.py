from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.domain.scheduling import (
    ScheduledTask,
    ScheduleTask,
    annotate_schedule,
    calculate_schedule,
    subtract_workdays,
)
from app.models.project import Project
from app.models.task import Task


def lock_project_schedule(db: Session, project_id: int) -> None:
    """Serialize schedule mutations and baseline capture for one project."""
    (
        db.query(Project.id)
        .filter(Project.id == project_id)
        .with_for_update()
        .one()
    )


def recalculate_schedule(
    tasks: list[Task],
    *,
    project_start: date,
    data_date: date | None = None,
) -> None:
    schedule = calculate_schedule(
        [
            ScheduleTask(
                id=task.id,
                name=task.name or "",
                duration=task.duration,
                predecessor_task_id=task.predecessor_task_id,
                dependency_type=task.dependency_type,
                lag_days=task.lag_days,
                parent_task_id=task.parent_task_id,
                manual_start_date=task.manual_start_date,
                progress_status=task.progress_status or "not_started",
                percent_complete=(
                    task.percent_complete
                    if task.percent_complete is not None
                    else 0
                ),
                actual_start_date=task.actual_start_date,
                actual_finish_date=task.actual_finish_date,
                remaining_duration=(
                    task.remaining_duration
                    if task.remaining_duration is not None
                    else task.duration
                ),
            )
            for task in tasks
        ],
        project_start=project_start,
        data_date=data_date or project_start,
    )

    for task, scheduled_task in zip(tasks, schedule, strict=True):
        task.start_date = scheduled_task.start_date
        task.end_date = scheduled_task.end_date
        task.duration = scheduled_task.duration


def _calculation_start(task: Task) -> str | None:
    remaining_duration = (
        task.remaining_duration
        if task.remaining_duration is not None
        else task.duration
    )
    if (
        task.progress_status == "in_progress"
        and task.end_date
        and remaining_duration > 0
    ):
        return subtract_workdays(
            date.fromisoformat(task.end_date),
            remaining_duration,
        ).isoformat()
    return task.start_date


def schedule_metadata(tasks: list[Task]) -> list[ScheduledTask]:
    return annotate_schedule(
        [
            ScheduledTask(
                id=task.id,
                name=task.name or "",
                duration=task.duration or 0,
                predecessor_task_id=task.predecessor_task_id,
                dependency_type=task.dependency_type,
                lag_days=task.lag_days,
                parent_task_id=task.parent_task_id,
                manual_start_date=task.manual_start_date,
                start_date=task.start_date,
                end_date=task.end_date,
                progress_status=task.progress_status or "not_started",
                percent_complete=(
                    task.percent_complete
                    if task.percent_complete is not None
                    else 0
                ),
                actual_start_date=task.actual_start_date,
                actual_finish_date=task.actual_finish_date,
                remaining_duration=(
                    task.remaining_duration
                    if task.remaining_duration is not None
                    else task.duration
                ),
                calculation_start_date=_calculation_start(task),
            )
            for task in tasks
        ]
    )


def annotate_critical_path(tasks: list[Task]) -> None:
    """Attach derived CPM metadata to ORM rows without persisting it."""
    annotated = schedule_metadata(tasks)

    for task, scheduled_task in zip(tasks, annotated, strict=True):
        task.is_critical = scheduled_task.is_critical
        task.total_float = scheduled_task.total_float


def task_response_rows(
    tasks: list[Task],
    *,
    annotated: list[ScheduledTask] | None = None,
) -> list[dict]:
    metadata_rows = (
        annotated if annotated is not None else schedule_metadata(tasks)
    )
    return [
        {
            "id": task.id,
            "name": task.name,
            "duration": task.duration,
            "predecessor": task.predecessor,
            "predecessor_task_id": task.predecessor_task_id,
            "dependency_type": task.dependency_type,
            "lag_days": task.lag_days,
            "start_date": task.start_date,
            "end_date": task.end_date,
            "manual_start_date": task.manual_start_date,
            "project_id": task.project_id,
            "order_index": task.order_index,
            "parent_task_id": task.parent_task_id,
            "is_collapsed": task.is_collapsed,
            "progress_status": metadata.progress_status,
            "percent_complete": metadata.percent_complete,
            "actual_start_date": metadata.actual_start_date,
            "actual_finish_date": metadata.actual_finish_date,
            "remaining_duration": metadata.remaining_duration,
            "status_updated_at": task.status_updated_at,
            "out_of_sequence": metadata.out_of_sequence,
            "out_of_sequence_reason": metadata.out_of_sequence_reason,
            "is_critical": metadata.is_critical,
            "total_float": metadata.total_float,
        }
        for task, metadata in zip(tasks, metadata_rows, strict=True)
    ]


def progress_summary(
    tasks: list[Task],
    *,
    data_date: date,
    annotated: list[ScheduledTask] | None = None,
) -> dict:
    metadata_rows = (
        annotated if annotated is not None else schedule_metadata(tasks)
    )
    parent_ids = {
        task.parent_task_id
        for task in tasks
        if task.parent_task_id is not None
    }
    leaves = [
        (task, metadata)
        for task, metadata in zip(tasks, metadata_rows, strict=True)
        if task.id not in parent_ids
    ]
    denominator = sum(task.duration for task, _ in leaves)
    weighted = sum(
        task.duration * metadata.percent_complete
        for task, metadata in leaves
    )
    trailing_start = data_date - timedelta(days=6)
    valid_finishes = [
        metadata.end_date
        for _, metadata in leaves
        if metadata.end_date is not None
    ]

    return {
        "total_leaf_tasks": len(leaves),
        "not_started_count": sum(
            metadata.progress_status == "not_started"
            for _, metadata in leaves
        ),
        "in_progress_count": sum(
            metadata.progress_status == "in_progress"
            for _, metadata in leaves
        ),
        "completed_count": sum(
            metadata.progress_status == "completed"
            for _, metadata in leaves
        ),
        "out_of_sequence_count": sum(
            metadata.out_of_sequence for _, metadata in leaves
        ),
        "percent_complete_weighted": (
            round(weighted / denominator, 1) if denominator else 0.0
        ),
        "data_date": data_date.isoformat(),
        "forecast_project_finish": (
            max(valid_finishes) if valid_finishes else None
        ),
        "completed_through_data_date": sum(
            metadata.progress_status == "completed"
            and metadata.actual_finish_date is not None
            and date.fromisoformat(metadata.actual_finish_date) <= data_date
            for _, metadata in leaves
        ),
        "tasks_started_last_7_days": sum(
            metadata.actual_start_date is not None
            and trailing_start
            <= date.fromisoformat(metadata.actual_start_date)
            <= data_date
            for _, metadata in leaves
        ),
        "tasks_completed_last_7_days": sum(
            metadata.actual_finish_date is not None
            and trailing_start
            <= date.fromisoformat(metadata.actual_finish_date)
            <= data_date
            for _, metadata in leaves
        ),
    }


def task_list_payload(tasks: list[Task], *, data_date: date) -> dict:
    annotated = schedule_metadata(tasks)
    return {
        "tasks": task_response_rows(tasks, annotated=annotated),
        "summary": progress_summary(
            tasks,
            data_date=data_date,
            annotated=annotated,
        ),
    }
