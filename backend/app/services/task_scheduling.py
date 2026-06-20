from datetime import date

from app.domain.scheduling import ScheduleTask, calculate_schedule
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
