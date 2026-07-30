from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.common import MAX_LONG_TEXT_LENGTH, ORMModel
from app.schemas.task import DateString


ChangeOrderStatus = Literal[
    "Draft",
    "Pending",
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Executed",
    "Void",
]
MoneyAmount = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
    ),
]


def normalize_optional_text(value: object) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    return normalized or None


def normalize_status(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


OptionalDateString = Annotated[
    DateString | None,
    BeforeValidator(normalize_optional_text),
]
NormalizedStatus = Annotated[
    ChangeOrderStatus,
    BeforeValidator(normalize_status),
]


def discard_legacy_number(value: object) -> object:
    if not isinstance(value, dict) or "co_number" not in value:
        return value

    normalized = dict(value)
    normalized.pop("co_number")
    return normalized


def validate_lifecycle_dates(
    requested_date: str | None,
    submitted_date: str | None,
    approved_date: str | None,
    executed_date: str | None,
) -> None:
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
            raise ValueError(
                f"{later_name} cannot be earlier than {earlier_name}"
            )


class ChangeOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    date: DateString
    company: str | None = Field(default=None, max_length=255)
    status: NormalizedStatus
    description: str | None = Field(
        default=None, max_length=MAX_LONG_TEXT_LENGTH
    )
    amount: str | None = Field(default=None, max_length=100)
    responsible_party: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=MAX_LONG_TEXT_LENGTH)
    proposed_amount: MoneyAmount | None = None
    approved_amount: MoneyAmount | None = None
    schedule_impact_days: int | None = Field(
        default=None, ge=-36_500, le=36_500
    )
    requested_date: OptionalDateString = None
    submitted_date: OptionalDateString = None
    approved_date: OptionalDateString = None
    executed_date: OptionalDateString = None

    @model_validator(mode="before")
    @classmethod
    def ignore_legacy_number(cls, value):
        return discard_legacy_number(value)

    @field_validator(
        "company",
        "description",
        "amount",
        "responsible_party",
        "title",
        "reason",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_combined_state(self):
        if not self.title and not self.description:
            raise ValueError("title or description is required")

        validate_lifecycle_dates(
            self.requested_date,
            self.submitted_date,
            self.approved_date,
            self.executed_date,
        )
        return self


class ChangeOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    date: DateString | None = None
    company: str | None = Field(default=None, max_length=255)
    status: NormalizedStatus | None = None
    description: str | None = Field(
        default=None, max_length=MAX_LONG_TEXT_LENGTH
    )
    amount: str | None = Field(default=None, max_length=100)
    responsible_party: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=MAX_LONG_TEXT_LENGTH)
    proposed_amount: MoneyAmount | None = None
    approved_amount: MoneyAmount | None = None
    schedule_impact_days: int | None = Field(
        default=None, ge=-36_500, le=36_500
    )
    requested_date: OptionalDateString = None
    submitted_date: OptionalDateString = None
    approved_date: OptionalDateString = None
    executed_date: OptionalDateString = None

    @model_validator(mode="before")
    @classmethod
    def ignore_legacy_number(cls, value):
        return discard_legacy_number(value)

    @field_validator(
        "company",
        "description",
        "amount",
        "responsible_party",
        "title",
        "reason",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return normalize_optional_text(value)

    @field_validator("date", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ChangeOrderResponse(ORMModel):
    id: int
    project_id: int
    date: str
    co_number: str
    company: str | None
    status: str
    description: str | None
    amount: str | None
    responsible_party: str | None
    title: str | None
    reason: str | None
    proposed_amount: Decimal | None
    approved_amount: Decimal | None
    schedule_impact_days: int | None
    requested_date: str | None
    submitted_date: str | None
    approved_date: str | None
    executed_date: str | None
    created_at: datetime
    updated_at: datetime


class ChangeOrderListResponse(BaseModel):
    change_orders: list[ChangeOrderResponse]
