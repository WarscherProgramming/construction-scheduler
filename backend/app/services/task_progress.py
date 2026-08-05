from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskProgressUpdate
from app.services.project_schedule_settings import (
    get_project_schedule_settings,
)
from app.services.task_scheduling import (
    lock_project_schedule,
    recalculate_schedule,
    task_list_payload,
)
from app.services.task_validation import validate_schedule_structure


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=message,
    )


def _validate_status_date(value: str | None, data_date: date, label: str) -> None:
    if value is not None and date.fromisoformat(value) > data_date:
        raise _unprocessable(f"{label} cannot be after the project Data Date")


def _normalized_progress_values(
    task: Task,
    payload: TaskProgressUpdate,
    *,
    data_date: date,
) -> dict:
    supplied = payload.model_dump(exclude_unset=True)
    target_status = supplied.get("progress_status", task.progress_status)
    if target_status is None:
        raise _unprocessable("progress_status cannot be null")

    if target_status == "not_started":
        expected_remaining = 0 if task.is_milestone else task.duration
        if (
            "percent_complete" in supplied
            and supplied["percent_complete"] != 0
        ):
            raise _unprocessable("Not Started tasks must be 0 percent complete")
        if supplied.get("actual_start_date") is not None:
            raise _unprocessable("Not Started tasks cannot have an Actual Start")
        if supplied.get("actual_finish_date") is not None:
            raise _unprocessable("Not Started tasks cannot have an Actual Finish")
        if (
            "remaining_duration" in supplied
            and supplied["remaining_duration"] != expected_remaining
        ):
            raise _unprocessable(
                "Not Started remaining duration must match planned duration"
            )
        return {
            "progress_status": "not_started",
            "percent_complete": 0,
            "actual_start_date": None,
            "actual_finish_date": None,
            "remaining_duration": expected_remaining,
        }

    if target_status == "in_progress":
        if task.is_milestone:
            raise _unprocessable(
                "Milestones cannot use the In Progress status"
            )
        actual_start = supplied.get(
            "actual_start_date",
            task.actual_start_date,
        )
        percent_complete = supplied.get(
            "percent_complete",
            task.percent_complete,
        )
        remaining_duration = supplied.get(
            "remaining_duration",
            task.remaining_duration,
        )
        if actual_start is None:
            raise _unprocessable("In Progress tasks require an Actual Start")
        if percent_complete is None or not 1 <= percent_complete <= 99:
            raise _unprocessable(
                "In Progress percent complete must be from 1 through 99"
            )
        if remaining_duration is None or remaining_duration < 1:
            raise _unprocessable(
                "In Progress remaining duration must be at least one workday"
            )
        if supplied.get("actual_finish_date") is not None:
            raise _unprocessable("In Progress tasks cannot have an Actual Finish")
        _validate_status_date(actual_start, data_date, "Actual Start")
        return {
            "progress_status": "in_progress",
            "percent_complete": percent_complete,
            "actual_start_date": actual_start,
            "actual_finish_date": None,
            "remaining_duration": remaining_duration,
        }

    actual_start = supplied.get("actual_start_date", task.actual_start_date)
    actual_finish = supplied.get("actual_finish_date", task.actual_finish_date)
    if actual_start is None or actual_finish is None:
        raise _unprocessable(
            "Completed tasks require an Actual Start and Actual Finish"
        )
    if "percent_complete" in supplied and supplied["percent_complete"] != 100:
        raise _unprocessable("Completed tasks must be 100 percent complete")
    if "remaining_duration" in supplied and supplied["remaining_duration"] != 0:
        raise _unprocessable("Completed tasks must have zero remaining duration")
    if date.fromisoformat(actual_finish) < date.fromisoformat(actual_start):
        raise _unprocessable("Actual Finish cannot be before Actual Start")
    _validate_status_date(actual_start, data_date, "Actual Start")
    _validate_status_date(actual_finish, data_date, "Actual Finish")
    return {
        "progress_status": "completed",
        "percent_complete": 100,
        "actual_start_date": actual_start,
        "actual_finish_date": actual_finish,
        "remaining_duration": 0,
    }


def update_task_progress(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    payload: TaskProgressUpdate,
    updated_by: int,
) -> dict:
    try:
        lock_project_schedule(db, project_id)
        settings = get_project_schedule_settings(db, project_id)
        tasks = (
            db.query(Task)
            .filter(Task.project_id == project_id)
            .order_by(Task.order_index, Task.id)
            .all()
        )
        task = next((item for item in tasks if item.id == task_id), None)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        if any(item.parent_task_id == task.id for item in tasks):
            raise _unprocessable(
                "Summary task progress is derived from its leaf tasks"
            )

        data_date = date.fromisoformat(settings.data_date)
        normalized = _normalized_progress_values(
            task,
            payload,
            data_date=data_date,
        )
        changed = any(
            getattr(task, field) != value
            for field, value in normalized.items()
        )
        if not changed:
            return task_list_payload(tasks, data_date=data_date)

        for field, value in normalized.items():
            setattr(task, field, value)
        task.status_updated_at = datetime.now(timezone.utc)
        task.status_updated_by = updated_by

        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=date.fromisoformat(settings.schedule_start_date),
            data_date=data_date,
        )
        db.commit()
        return task_list_payload(tasks, data_date=data_date)
    except Exception:
        db.rollback()
        raise
