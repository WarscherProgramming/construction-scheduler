from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.schemas.dashboard import DashboardResponse
from app.schemas.task import DateString
from app.services.dashboard import get_project_dashboard


router = APIRouter()


@router.get(
    "/projects/{project_id}/dashboard",
    response_model=DashboardResponse,
)
def get_dashboard(
    project_id: int,
    as_of: DateString,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return get_project_dashboard(
        db,
        project,
        date.fromisoformat(as_of),
    )
