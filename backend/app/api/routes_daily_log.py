
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.daily_log import DailyLog
from app.models.project import Project
from app.core.security import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_project_owner(project_id: int, user_id: int, db: Session):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project"
        )

    return project


def daily_log_to_dict(log):
    return {
        "id": log.id,
        "project_id": log.project_id,
        "date": log.date,
        "company": log.company,
        "manpower": log.manpower,
        "work_performed": log.work_performed,
        "delays": log.delays,
        "notes": log.notes,
    }


@router.get("/projects/{project_id}/daily-logs")
def get_daily_logs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    logs = (
        db.query(DailyLog)
        .filter(DailyLog.project_id == project_id)
        .order_by(DailyLog.date.desc())
        .all()
    )

    return {"daily_logs": [daily_log_to_dict(log) for log in logs]}


@router.post("/projects/{project_id}/daily-logs")
def create_daily_log(
    project_id: int,
    log: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    new_log = DailyLog(
        project_id=project_id,
        date=log["date"],
        company=log["company"],
        manpower=log["manpower"],
        work_performed=log.get("work_performed"),
        delays=log.get("delays"),
        notes=log.get("notes"),
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return daily_log_to_dict(new_log)