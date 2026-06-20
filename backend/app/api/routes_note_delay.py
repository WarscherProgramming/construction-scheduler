
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.note_delay import NoteDelay
from app.models.project import Project
from app.schemas.note_delay import (
    NoteDelayCreate,
    NoteDelayListResponse,
    NoteDelayResponse,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/notes-delays",
    response_model=NoteDelayListResponse,
)
def get_notes_delays(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    entries = (
        db.query(NoteDelay)
        .filter(NoteDelay.project_id == project_id)
        .order_by(NoteDelay.date.desc())
        .all()
    )

    return {"notes_delays": entries}


@router.post(
    "/projects/{project_id}/notes-delays",
    response_model=NoteDelayResponse,
    status_code=201,
)
def create_note_delay(
    project_id: int,
    entry: NoteDelayCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_entry = NoteDelay(
        project_id=project_id,
        **entry.model_dump(),
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return new_entry
