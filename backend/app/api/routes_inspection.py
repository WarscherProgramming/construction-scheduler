
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.inspection import Inspection
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


def inspection_to_dict(inspection):
    return {
        "id": inspection.id,
        "project_id": inspection.project_id,
        "date": inspection.date,
        "inspection_type": inspection.inspection_type,
        "inspector": inspection.inspector,
        "status": inspection.status,
        "notes": inspection.notes,
        "corrective_action": inspection.corrective_action,
    }


@router.get("/projects/{project_id}/inspections")
def get_inspections(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    inspections = (
        db.query(Inspection)
        .filter(Inspection.project_id == project_id)
        .order_by(Inspection.date.desc())
        .all()
    )

    return {
        "inspections": [
            inspection_to_dict(inspection)
            for inspection in inspections
        ]
    }


@router.post("/projects/{project_id}/inspections")
def create_inspection(
    project_id: int,
    inspection: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    new_inspection = Inspection(
        project_id=project_id,
        date=inspection["date"],
        inspection_type=inspection["inspection_type"],
        inspector=inspection.get("inspector"),
        status=inspection["status"],
        notes=inspection.get("notes"),
        corrective_action=inspection.get("corrective_action"),
    )

    db.add(new_inspection)
    db.commit()
    db.refresh(new_inspection)

    return inspection_to_dict(new_inspection)