
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.note_delay import NoteDelay
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


def note_delay_to_dict(entry):
    return {
        "id": entry.id,
        "project_id": entry.project_id,
        "date": entry.date,
        "entry_type": entry.entry_type,
        "company": entry.company,
        "description": entry.description,
        "impact": entry.impact,
    }


@router.get("/projects/{project_id}/notes-delays")
def get_notes_delays(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    entries = (
        db.query(NoteDelay)
        .filter(NoteDelay.project_id == project_id)
        .order_by(NoteDelay.date.desc())
        .all()
    )

    return {
        "notes_delays": [
            note_delay_to_dict(entry)
            for entry in entries
        ]
    }


@router.post("/projects/{project_id}/notes-delays")
def create_note_delay(
    project_id: int,
    entry: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    new_entry = NoteDelay(
        project_id=project_id,
        date=entry["date"],
        entry_type=entry["entry_type"],
        company=entry.get("company"),
        description=entry["description"],
        impact=entry.get("impact"),
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return note_delay_to_dict(new_entry)