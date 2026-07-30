from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import (
    MAX_LONG_TEXT_LENGTH,
    MutationModel,
    ORMModel,
    UpdateMutationModel,
)
from app.schemas.task import DateString


PunchItemPriority = Literal["Low", "Medium", "High", "Critical"]
PunchItemStatus = Literal["Open", "In Progress", "Completed", "Verified"]
RequiredLocation = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
RequiredDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_LONG_TEXT_LENGTH,
    ),
]


def validate_date_order(
    due_date: str | None,
    completed_date: str | None,
) -> None:
    if due_date and completed_date and completed_date < due_date:
        raise ValueError(
            "completed_date cannot be earlier than due_date"
        )


class PunchItemCreate(MutationModel):
    location: RequiredLocation
    trade: str | None = Field(default=None, max_length=255)
    description: RequiredDescription
    responsible_company: str | None = Field(default=None, max_length=255)
    assigned_to: str | None = Field(default=None, max_length=255)
    priority: PunchItemPriority = "Medium"
    status: PunchItemStatus = "Open"
    due_date: DateString | None = None
    completed_date: DateString | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_date_order(self.due_date, self.completed_date)
        return self


class PunchItemUpdate(UpdateMutationModel):
    location: RequiredLocation | None = None
    trade: str | None = Field(default=None, max_length=255)
    description: RequiredDescription | None = None
    responsible_company: str | None = Field(default=None, max_length=255)
    assigned_to: str | None = Field(default=None, max_length=255)
    priority: PunchItemPriority | None = None
    status: PunchItemStatus | None = None
    due_date: DateString | None = None
    completed_date: DateString | None = None

    @field_validator("location", "description", "priority", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        validate_date_order(self.due_date, self.completed_date)
        return self


class PunchItemResponse(ORMModel):
    id: int
    project_id: int
    number: str
    location: str
    trade: str | None
    description: str
    responsible_company: str | None
    assigned_to: str | None
    priority: PunchItemPriority
    status: PunchItemStatus
    due_date: str | None
    completed_date: str | None
    created_at: datetime
    updated_at: datetime


class PunchItemListResponse(BaseModel):
    punch_items: list[PunchItemResponse]
