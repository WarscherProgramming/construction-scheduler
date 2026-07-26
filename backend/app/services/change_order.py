from decimal import Decimal, InvalidOperation
import re

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.change_order import ChangeOrder, ChangeOrderNumberSequence
from app.models.project import Project
from app.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate


CHANGE_ORDER_NUMBER_PATTERN = re.compile(r"^CO-(\d+)$")
MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY_VALUE = Decimal("999999999999.99")


def parse_legacy_amount(value: str | None) -> Decimal | None:
    if value is None:
        return None

    normalized = value.strip().replace("$", "").replace(",", "")
    if not normalized:
        return None

    try:
        amount = Decimal(normalized)
        quantized_amount = amount.quantize(MONEY_QUANTUM)
    except InvalidOperation:
        return None

    if (
        not amount.is_finite()
        or amount < 0
        or amount > MAX_MONEY_VALUE
        or amount != quantized_amount
    ):
        return None

    return amount


def allocate_change_order_number(db: Session, project_id: int) -> str:
    db.query(Project).filter(Project.id == project_id).with_for_update().one()

    sequence = (
        db.query(ChangeOrderNumberSequence)
        .filter(ChangeOrderNumberSequence.project_id == project_id)
        .first()
    )

    if sequence is None:
        existing_numbers = (
            db.query(ChangeOrder.co_number)
            .filter(ChangeOrder.project_id == project_id)
            .all()
        )
        last_number = max(
            (
                int(match.group(1))
                for (number,) in existing_numbers
                if (match := CHANGE_ORDER_NUMBER_PATTERN.fullmatch(number))
            ),
            default=0,
        )
        sequence = ChangeOrderNumberSequence(
            project_id=project_id,
            last_number=last_number + 1,
        )
        db.add(sequence)
    else:
        sequence.last_number += 1

    return f"CO-{sequence.last_number:03d}"


def validate_change_order_state(
    *,
    title: str | None,
    description: str | None,
    requested_date: str | None,
    submitted_date: str | None,
    approved_date: str | None,
    executed_date: str | None,
) -> None:
    if not title and not description:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="title or description is required",
        )

    ordered_dates = (
        ("requested_date", requested_date),
        ("submitted_date", submitted_date),
        ("approved_date", approved_date),
        ("executed_date", executed_date),
    )

    for (earlier_name, earlier), (later_name, later) in zip(
        ordered_dates,
        ordered_dates[1:],
    ):
        if earlier and later and later < earlier:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"{later_name} cannot be earlier than {earlier_name}"
                ),
            )


def get_project_change_order(
    db: Session,
    project_id: int,
    change_order_id: int,
) -> ChangeOrder:
    change_order = (
        db.query(ChangeOrder)
        .filter(
            ChangeOrder.id == change_order_id,
            ChangeOrder.project_id == project_id,
        )
        .first()
    )

    if change_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change order not found",
        )

    return change_order


def list_change_orders(db: Session, project_id: int) -> list[ChangeOrder]:
    return (
        db.query(ChangeOrder)
        .filter(ChangeOrder.project_id == project_id)
        .order_by(ChangeOrder.date.desc(), ChangeOrder.id.desc())
        .all()
    )


def create_change_order(
    db: Session,
    project_id: int,
    payload: ChangeOrderCreate,
) -> ChangeOrder:
    values = payload.model_dump()
    if values["proposed_amount"] is None:
        values["proposed_amount"] = parse_legacy_amount(values["amount"])

    validate_change_order_state(
        title=values["title"],
        description=values["description"],
        requested_date=values["requested_date"],
        submitted_date=values["submitted_date"],
        approved_date=values["approved_date"],
        executed_date=values["executed_date"],
    )

    change_order = ChangeOrder(
        project_id=project_id,
        co_number=allocate_change_order_number(db, project_id),
        **values,
    )
    db.add(change_order)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Change order number already exists for this project",
        ) from error

    db.refresh(change_order)
    return change_order


def update_change_order(
    db: Session,
    change_order: ChangeOrder,
    payload: ChangeOrderUpdate,
) -> ChangeOrder:
    values = payload.model_dump(exclude_unset=True)
    combined = {
        field: values.get(field, getattr(change_order, field))
        for field in (
            "title",
            "description",
            "requested_date",
            "submitted_date",
            "approved_date",
            "executed_date",
        )
    }
    validate_change_order_state(**combined)

    for field, value in values.items():
        setattr(change_order, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Change order number already exists for this project",
        ) from error

    db.refresh(change_order)
    return change_order


def delete_change_order(db: Session, change_order: ChangeOrder) -> None:
    db.delete(change_order)
    db.commit()
