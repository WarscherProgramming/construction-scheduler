
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.daily_log import DailyLog
from app.models.project import Project
from app.schemas.daily_log import (
    DailyLogCreate,
    DailyLogListResponse,
    DailyLogResponse,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/daily-logs",
    response_model=DailyLogListResponse,
)
def get_daily_logs(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    logs = (
        db.query(DailyLog)
        .filter(DailyLog.project_id == project_id)
        .order_by(DailyLog.date.desc())
        .all()
    )

    return {"daily_logs": logs}


@router.post(
    "/projects/{project_id}/daily-logs",
    response_model=DailyLogResponse,
    status_code=201,
)
def create_daily_log(
    project_id: int,
    log: DailyLogCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_log = DailyLog(
        project_id=project_id,
        **log.model_dump(),
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return new_log
