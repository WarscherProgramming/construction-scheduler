from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import ORMModel
from app.schemas.task import DateString


RFIStatus = Literal["Open", "Pending", "Closed"]
RequiredText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
RFISubject = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class RFICreate(BaseModel):
    subject: RFISubject
    question: RequiredText
    responsible_company: str | None = Field(default=None, max_length=255)
    submitted_date: DateString
    due_date: DateString | None = None
    response: str | None = None
    status: RFIStatus = "Open"

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.due_date and self.due_date < self.submitted_date:
            raise ValueError(
                "due_date cannot be earlier than submitted_date"
            )
        return self


class RFIUpdate(BaseModel):
    subject: RFISubject | None = None
    question: RequiredText | None = None
    responsible_company: str | None = Field(default=None, max_length=255)
    submitted_date: DateString | None = None
    due_date: DateString | None = None
    response: str | None = None
    status: RFIStatus | None = None

    @field_validator("subject", "question", "submitted_date", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_date_order(self):
        if (
            self.submitted_date
            and self.due_date
            and self.due_date < self.submitted_date
        ):
            raise ValueError(
                "due_date cannot be earlier than submitted_date"
            )
        return self


class RFIResponse(ORMModel):
    id: int
    project_id: int
    number: str
    subject: str
    question: str
    responsible_company: str | None
    submitted_date: str
    due_date: str | None
    response: str | None
    status: RFIStatus
    created_at: datetime
    updated_at: datetime


class RFIListResponse(BaseModel):
    rfis: list[RFIResponse]
