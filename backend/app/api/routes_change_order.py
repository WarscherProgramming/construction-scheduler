
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.change_order import ChangeOrder
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
        raise HTTPException(status_code=403, detail="You do not have access to this project")

    return project


def change_order_to_dict(co):
    return {
        "id": co.id,
        "project_id": co.project_id,
        "date": co.date,
        "co_number": co.co_number,
        "company": co.company,
        "status": co.status,
        "description": co.description,
        "amount": co.amount,
        "responsible_party": co.responsible_party,
    }


@router.get("/projects/{project_id}/change-orders")
def get_change_orders(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    change_orders = (
        db.query(ChangeOrder)
        .filter(ChangeOrder.project_id == project_id)
        .order_by(ChangeOrder.date.desc())
        .all()
    )

    return {"change_orders": [change_order_to_dict(co) for co in change_orders]}


@router.post("/projects/{project_id}/change-orders")
def create_change_order(
    project_id: int,
    change_order: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    new_change_order = ChangeOrder(
        project_id=project_id,
        date=change_order["date"],
        co_number=change_order["co_number"],
        company=change_order.get("company"),
        status=change_order["status"],
        description=change_order.get("description"),
        amount=change_order.get("amount"),
        responsible_party=change_order.get("responsible_party"),
    )

    db.add(new_change_order)
    db.commit()
    db.refresh(new_change_order)

    return change_order_to_dict(new_change_order)

@router.delete("/projects/{project_id}/change-orders/{change_order_id}")
def delete_change_order(
    project_id: int,
    change_order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

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
            status_code=404,
            detail="Change order not found"
        )

    db.delete(change_order)
    db.commit()

    return {"message": "Change order deleted"}