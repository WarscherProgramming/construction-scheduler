from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_attachment_config,
    get_attachment_storage_resolver,
    get_db,
    get_owned_project,
)
from app.core.config import AttachmentConfig
from app.models.project import Project
from app.models.punch_item import PunchItem
from app.schemas.common import MessageResponse
from app.schemas.punch_item import (
    PunchItemCreate,
    PunchItemListResponse,
    PunchItemResponse,
    PunchItemUpdate,
)
from app.services.punch_item import (
    allocate_punch_item_number,
    delete_punch_item as delete_punch_item_record,
    validate_punch_item_dates,
)
from app.services.attachment_cleanup import StorageResolver

router = APIRouter()


def get_project_punch_item(
    db: Session,
    project_id: int,
    item_id: int,
) -> PunchItem:
    punch_item = (
        db.query(PunchItem)
        .filter(
            PunchItem.id == item_id,
            PunchItem.project_id == project_id,
        )
        .first()
    )

    if punch_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Punch Item not found",
        )

    return punch_item


@router.get(
    "/projects/{project_id}/punch-items",
    response_model=PunchItemListResponse,
)
def get_punch_items(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    punch_items = (
        db.query(PunchItem)
        .filter(PunchItem.project_id == project_id)
        .order_by(PunchItem.due_date.desc(), PunchItem.id.desc())
        .all()
    )

    return {"punch_items": punch_items}


@router.post(
    "/projects/{project_id}/punch-items",
    response_model=PunchItemResponse,
    status_code=201,
)
def create_punch_item(
    project_id: int,
    punch_item: PunchItemCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_punch_item = PunchItem(
        project_id=project_id,
        number=allocate_punch_item_number(db, project_id),
        **punch_item.model_dump(),
    )

    db.add(new_punch_item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Punch Item number already exists for this project"
            ),
        ) from error

    db.refresh(new_punch_item)
    return new_punch_item


@router.put(
    "/projects/{project_id}/punch-items/{item_id}",
    response_model=PunchItemResponse,
)
def update_punch_item(
    project_id: int,
    item_id: int,
    updated_punch_item: PunchItemUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    punch_item = get_project_punch_item(db, project_id, item_id)
    values = updated_punch_item.model_dump(exclude_unset=True)
    due_date = values.get("due_date", punch_item.due_date)
    completed_date = values.get(
        "completed_date",
        punch_item.completed_date,
    )
    validate_punch_item_dates(due_date, completed_date)

    for field, value in values.items():
        setattr(punch_item, field, value)

    db.commit()
    db.refresh(punch_item)
    return punch_item


@router.delete(
    "/projects/{project_id}/punch-items/{item_id}",
    response_model=MessageResponse,
)
def delete_punch_item(
    project_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    config: AttachmentConfig = Depends(get_attachment_config),
    storage_resolver: StorageResolver = Depends(
        get_attachment_storage_resolver
    ),
):
    punch_item = get_project_punch_item(db, project_id, item_id)

    delete_punch_item_record(
        db,
        punch_item,
        config,
        storage_resolver,
    )

    return {"message": "Punch Item deleted"}
