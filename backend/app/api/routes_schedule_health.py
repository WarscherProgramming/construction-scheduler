from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.schemas.resource_planning import PositiveId
from app.schemas.schedule_health import ScheduleHealthResponse
from app.services.schedule_health import get_schedule_health


router = APIRouter()


@router.get(
    "/projects/{project_id}/schedule-health",
    response_model=ScheduleHealthResponse,
)
def get_project_schedule_health(
    project_id: int,
    baseline_id: Annotated[PositiveId | None, Query()] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return get_schedule_health(
        db,
        project_id=project_id,
        baseline_id=baseline_id,
    )

