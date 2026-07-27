from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.project import Project
from app.models.punch_item import PunchItem, PunchItemNumberSequence
from app.services.attachment import delete_parent_with_attachments
from app.services.attachment_cleanup import StorageResolver


def allocate_punch_item_number(db: Session, project_id: int) -> str:
    db.query(Project).filter(Project.id == project_id).with_for_update().one()

    sequence = (
        db.query(PunchItemNumberSequence)
        .filter(PunchItemNumberSequence.project_id == project_id)
        .first()
    )

    if sequence is None:
        existing_numbers = (
            db.query(PunchItem.number)
            .filter(PunchItem.project_id == project_id)
            .all()
        )
        last_number = max(
            (
                int(number.removeprefix("PUNCH-"))
                for (number,) in existing_numbers
                if number.removeprefix("PUNCH-").isdigit()
            ),
            default=0,
        )
        sequence = PunchItemNumberSequence(
            project_id=project_id,
            last_number=last_number + 1,
        )
        db.add(sequence)
    else:
        sequence.last_number += 1

    return f"PUNCH-{sequence.last_number:03d}"


def validate_punch_item_dates(
    due_date: str | None,
    completed_date: str | None,
) -> None:
    if due_date and completed_date and completed_date < due_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="completed_date cannot be earlier than due_date",
        )


def delete_punch_item(
    db: Session,
    punch_item: PunchItem,
    config: AttachmentConfig,
    storage_resolver: StorageResolver,
) -> None:
    delete_parent_with_attachments(
        db,
        punch_item,
        punch_item.project_id,
        "punch_item",
        punch_item.id,
        config=config,
        storage_resolver=storage_resolver,
    )
