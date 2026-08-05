from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.models.task import Task
from app.schemas.project_schedule_settings import (
    ProjectScheduleSettingsResponse,
    ProjectScheduleSettingsUpdate,
)
from app.services.project_schedule_settings import (
    get_project_schedule_settings,
)
from app.services.task_scheduling import (
    lock_project_schedule,
    recalculate_schedule,
)
from app.services.task_validation import validate_schedule_structure


router = APIRouter()


@router.get(
    "/projects/{project_id}/schedule-settings",
    response_model=ProjectScheduleSettingsResponse,
)
def get_schedule_settings(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return get_project_schedule_settings(db, project_id)


@router.put(
    "/projects/{project_id}/schedule-settings",
    response_model=ProjectScheduleSettingsResponse,
)
def update_schedule_settings(
    project_id: int,
    payload: ProjectScheduleSettingsUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    lock_project_schedule(db, project_id)
    settings = get_project_schedule_settings(db, project_id)
    values = payload.model_dump(exclude_unset=True)
    if all(getattr(settings, field) == value for field, value in values.items()):
        return settings

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    try:
        next_schedule_start = values.get(
            "schedule_start_date",
            settings.schedule_start_date,
        )
        next_data_date = values.get("data_date", settings.data_date)
        parsed_data_date = date.fromisoformat(next_data_date)
        future_actual = next(
            (
                task
                for task in tasks
                if (
                    task.actual_start_date
                    and date.fromisoformat(task.actual_start_date)
                    > parsed_data_date
                )
                or (
                    task.actual_finish_date
                    and date.fromisoformat(task.actual_finish_date)
                    > parsed_data_date
                )
            ),
            None,
        )
        if future_actual is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Data Date cannot be earlier than recorded task actuals"
                ),
            )

        settings.schedule_start_date = next_schedule_start
        settings.data_date = next_data_date
        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=date.fromisoformat(next_schedule_start),
            data_date=parsed_data_date,
        )
        db.commit()
        db.refresh(settings)
    except Exception:
        db.rollback()
        raise

    return settings
