from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.models.submittal import Submittal
from app.schemas.common import MessageResponse
from app.schemas.submittal import (
    SubmittalCreate,
    SubmittalListResponse,
    SubmittalResponse,
    SubmittalUpdate,
)
from app.services.submittal import (
    allocate_submittal_number,
    validate_submittal_dates,
)

router = APIRouter()


def get_project_submittal(
    db: Session,
    project_id: int,
    submittal_id: int,
) -> Submittal:
    submittal = (
        db.query(Submittal)
        .filter(
            Submittal.id == submittal_id,
            Submittal.project_id == project_id,
        )
        .first()
    )

    if submittal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submittal not found",
        )

    return submittal


@router.get(
    "/projects/{project_id}/submittals",
    response_model=SubmittalListResponse,
)
def get_submittals(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    submittals = (
        db.query(Submittal)
        .filter(Submittal.project_id == project_id)
        .order_by(Submittal.submitted_date.desc(), Submittal.id.desc())
        .all()
    )

    return {"submittals": submittals}


@router.post(
    "/projects/{project_id}/submittals",
    response_model=SubmittalResponse,
    status_code=201,
)
def create_submittal(
    project_id: int,
    submittal: SubmittalCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_submittal = Submittal(
        project_id=project_id,
        number=allocate_submittal_number(db, project_id),
        **submittal.model_dump(),
    )

    db.add(new_submittal)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Submittal number already exists for this project"
            ),
        ) from error

    db.refresh(new_submittal)
    return new_submittal


@router.put(
    "/projects/{project_id}/submittals/{submittal_id}",
    response_model=SubmittalResponse,
)
def update_submittal(
    project_id: int,
    submittal_id: int,
    updated_submittal: SubmittalUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    submittal = get_project_submittal(db, project_id, submittal_id)
    values = updated_submittal.model_dump(exclude_unset=True)
    submitted_date = values.get(
        "submitted_date",
        submittal.submitted_date,
    )
    required_by_date = values.get(
        "required_by_date",
        submittal.required_by_date,
    )
    reviewed_date = values.get(
        "reviewed_date",
        submittal.reviewed_date,
    )
    validate_submittal_dates(
        submitted_date,
        required_by_date,
        reviewed_date,
    )

    for field, value in values.items():
        setattr(submittal, field, value)

    db.commit()
    db.refresh(submittal)
    return submittal


@router.delete(
    "/projects/{project_id}/submittals/{submittal_id}",
    response_model=MessageResponse,
)
def delete_submittal(
    project_id: int,
    submittal_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    submittal = get_project_submittal(db, project_id, submittal_id)

    db.delete(submittal)
    db.commit()

    return {"message": "Submittal deleted"}
