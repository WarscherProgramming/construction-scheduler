from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_attachment_config,
    get_attachment_storage_resolver,
    get_db,
    get_owned_project,
)
from app.core.config import AttachmentConfig
from app.models.project import Project
from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderListResponse,
    ChangeOrderResponse,
    ChangeOrderUpdate,
)
from app.schemas.common import MessageResponse
from app.services.change_order import (
    create_change_order as create_change_order_record,
    delete_change_order as delete_change_order_record,
    get_project_change_order,
    list_change_orders,
    update_change_order as update_change_order_record,
)
from app.services.attachment_cleanup import StorageResolver

router = APIRouter()


@router.get(
    "/projects/{project_id}/change-orders",
    response_model=ChangeOrderListResponse,
)
def get_change_orders(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"change_orders": list_change_orders(db, project_id)}


@router.post(
    "/projects/{project_id}/change-orders",
    response_model=ChangeOrderResponse,
    status_code=201,
)
def create_change_order(
    project_id: int,
    change_order: ChangeOrderCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return create_change_order_record(db, project_id, change_order)


@router.put(
    "/projects/{project_id}/change-orders/{change_order_id}",
    response_model=ChangeOrderResponse,
)
def update_change_order(
    project_id: int,
    change_order_id: int,
    updated_change_order: ChangeOrderUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    change_order = get_project_change_order(
        db,
        project_id,
        change_order_id,
    )
    return update_change_order_record(db, change_order, updated_change_order)


@router.delete(
    "/projects/{project_id}/change-orders/{change_order_id}",
    response_model=MessageResponse,
)
def delete_change_order(
    project_id: int,
    change_order_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    config: AttachmentConfig = Depends(get_attachment_config),
    storage_resolver: StorageResolver = Depends(
        get_attachment_storage_resolver
    ),
):
    change_order = get_project_change_order(
        db,
        project_id,
        change_order_id,
    )
    delete_change_order_record(
        db,
        change_order,
        config,
        storage_resolver,
    )
    return {"message": "Change order deleted"}
