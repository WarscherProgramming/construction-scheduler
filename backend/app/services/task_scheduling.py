from datetime import date

from app.domain.scheduling import (
    ScheduledTask,
    ScheduleTask,
    apply_critical_path,
    calculate_schedule,
)
from app.models.task import Task


def recalculate_schedule(
    tasks: list[Task],
    *,
    project_start: date | None = None,
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
            )
            for task in tasks
        ],
        project_start=project_start or date.today(),
    )

    for task, scheduled_task in zip(tasks, schedule, strict=True):
        task.start_date = scheduled_task.start_date
        task.end_date = scheduled_task.end_date
        task.duration = scheduled_task.duration


def annotate_critical_path(tasks: list[Task]) -> None:
    """Attach derived `is_critical` / `total_float` to ORM tasks for responses.

    Computed from the stored schedule on every read — the values are pure
    derivations of dates and dependencies, so nothing is persisted.
    """
    annotated = apply_critical_path(
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
            )
            for task in tasks
        ]
    )

    for task, scheduled_task in zip(tasks, annotated, strict=True):
        task.is_critical = scheduled_task.is_critical
        task.total_float = scheduled_task.total_float
