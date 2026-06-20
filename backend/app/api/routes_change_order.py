
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.change_order import ChangeOrder
from app.models.project import Project
from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderListResponse,
    ChangeOrderResponse,
)
from app.schemas.common import MessageResponse

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
    change_orders = (
        db.query(ChangeOrder)
        .filter(ChangeOrder.project_id == project_id)
        .order_by(ChangeOrder.date.desc())
        .all()
    )

    return {"change_orders": change_orders}


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
    new_change_order = ChangeOrder(
        project_id=project_id,
        **change_order.model_dump(),
    )

    db.add(new_change_order)
    db.commit()
    db.refresh(new_change_order)

    return new_change_order

@router.delete(
    "/projects/{project_id}/change-orders/{change_order_id}",
    response_model=MessageResponse,
)
def delete_change_order(
    project_id: int,
    change_order_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    change_order = (
        db.query(ChangeOrder)
        .filter(
            ChangeOrder.id == change_order_id,
            ChangeOrder.project_id == project_id,
        )
        .first()
    )

    if not change_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change order not found"
        )

    db.delete(change_order)
    db.commit()

    return {"message": "Change order deleted"}
