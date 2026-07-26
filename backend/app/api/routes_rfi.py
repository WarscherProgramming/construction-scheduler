from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.models.rfi import RFI
from app.schemas.common import MessageResponse
from app.schemas.rfi import (
    RFICreate,
    RFIListResponse,
    RFIResponse,
    RFIUpdate,
)
from app.services.rfi import allocate_rfi_number, validate_rfi_dates

router = APIRouter()


def get_project_rfi(
    db: Session,
    project_id: int,
    rfi_id: int,
) -> RFI:
    rfi = (
        db.query(RFI)
        .filter(RFI.id == rfi_id, RFI.project_id == project_id)
        .first()
    )

    if rfi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFI not found",
        )

    return rfi


@router.get(
    "/projects/{project_id}/rfis",
    response_model=RFIListResponse,
)
def get_rfis(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    rfis = (
        db.query(RFI)
        .filter(RFI.project_id == project_id)
        .order_by(RFI.submitted_date.desc(), RFI.id.desc())
        .all()
    )

    return {"rfis": rfis}


@router.post(
    "/projects/{project_id}/rfis",
    response_model=RFIResponse,
    status_code=201,
)
def create_rfi(
    project_id: int,
    rfi: RFICreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_rfi = RFI(
        project_id=project_id,
        number=allocate_rfi_number(db, project_id),
        **rfi.model_dump(),
    )

    db.add(new_rfi)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RFI number already exists for this project",
        ) from error

    db.refresh(new_rfi)
    return new_rfi


@router.put(
    "/projects/{project_id}/rfis/{rfi_id}",
    response_model=RFIResponse,
)
def update_rfi(
    project_id: int,
    rfi_id: int,
    updated_rfi: RFIUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    rfi = get_project_rfi(db, project_id, rfi_id)
    values = updated_rfi.model_dump(exclude_unset=True)
    submitted_date = values.get("submitted_date", rfi.submitted_date)
    due_date = values.get("due_date", rfi.due_date)
    validate_rfi_dates(submitted_date, due_date)

    for field, value in values.items():
        setattr(rfi, field, value)

    db.commit()
    db.refresh(rfi)
    return rfi


@router.delete(
    "/projects/{project_id}/rfis/{rfi_id}",
    response_model=MessageResponse,
)
def delete_rfi(
    project_id: int,
    rfi_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    rfi = get_project_rfi(db, project_id, rfi_id)

    db.delete(rfi)
    db.commit()

    return {"message": "RFI deleted"}
