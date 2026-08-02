from datetime import date

from fastapi import APIRouter, Depends
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
    if settings.schedule_start_date == payload.schedule_start_date:
        return settings

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    try:
        settings.schedule_start_date = payload.schedule_start_date
        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=date.fromisoformat(payload.schedule_start_date),
        )
        db.commit()
        db.refresh(settings)
    except Exception:
        db.rollback()
        raise

    return settings
