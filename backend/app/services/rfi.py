from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.project import Project
from app.models.rfi import RFI, RFINumberSequence
from app.services.attachment import delete_parent_with_attachments
from app.services.attachment_cleanup import StorageResolver


def allocate_rfi_number(db: Session, project_id: int) -> str:
    db.query(Project).filter(Project.id == project_id).with_for_update().one()

    sequence = (
        db.query(RFINumberSequence)
        .filter(RFINumberSequence.project_id == project_id)
        .first()
    )

    if sequence is None:
        existing_numbers = (
            db.query(RFI.number)
            .filter(RFI.project_id == project_id)
            .all()
        )
        last_number = max(
            (
                int(number.removeprefix("RFI-"))
                for (number,) in existing_numbers
                if number.removeprefix("RFI-").isdigit()
            ),
            default=0,
        )
        sequence = RFINumberSequence(
            project_id=project_id,
            last_number=last_number + 1,
        )
        db.add(sequence)
    else:
        sequence.last_number += 1

    return f"RFI-{sequence.last_number:03d}"


def validate_rfi_dates(
    submitted_date: str,
    due_date: str | None,
) -> None:
    if due_date and due_date < submitted_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="due_date cannot be earlier than submitted_date",
        )


def delete_rfi(
    db: Session,
    rfi: RFI,
    config: AttachmentConfig,
    storage_resolver: StorageResolver,
) -> None:
    delete_parent_with_attachments(
        db,
        rfi,
        rfi.project_id,
        "rfi",
        rfi.id,
        config=config,
        storage_resolver=storage_resolver,
    )
