from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.submittal import Submittal, SubmittalNumberSequence


def allocate_submittal_number(db: Session, project_id: int) -> str:
    db.query(Project).filter(Project.id == project_id).with_for_update().one()

    sequence = (
        db.query(SubmittalNumberSequence)
        .filter(SubmittalNumberSequence.project_id == project_id)
        .first()
    )

    if sequence is None:
        existing_numbers = (
            db.query(Submittal.number)
            .filter(Submittal.project_id == project_id)
            .all()
        )
        last_number = max(
            (
                int(number.removeprefix("SUB-"))
                for (number,) in existing_numbers
                if number.removeprefix("SUB-").isdigit()
            ),
            default=0,
        )
        sequence = SubmittalNumberSequence(
            project_id=project_id,
            last_number=last_number + 1,
        )
        db.add(sequence)
    else:
        sequence.last_number += 1

    return f"SUB-{sequence.last_number:03d}"


def validate_submittal_dates(
    submitted_date: str | None,
    required_by_date: str | None,
    reviewed_date: str | None,
) -> None:
    if (
        submitted_date
        and required_by_date
        and required_by_date < submitted_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "required_by_date cannot be earlier than submitted_date"
            ),
        )

    if (
        submitted_date
        and reviewed_date
        and reviewed_date < submitted_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="reviewed_date cannot be earlier than submitted_date",
        )
