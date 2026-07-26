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


SubmittalStatus = Literal[
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
    "Revise and Resubmit",
    "Rejected",
]
SubmittalTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
SpecificationSection = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


def validate_date_order(
    submitted_date: str | None,
    required_by_date: str | None,
    reviewed_date: str | None,
) -> None:
    if (
        submitted_date
        and required_by_date
        and required_by_date < submitted_date
    ):
        raise ValueError(
            "required_by_date cannot be earlier than submitted_date"
        )

    if (
        submitted_date
        and reviewed_date
        and reviewed_date < submitted_date
    ):
        raise ValueError(
            "reviewed_date cannot be earlier than submitted_date"
        )


class SubmittalCreate(BaseModel):
    specification_section: SpecificationSection
    title: SubmittalTitle
    responsible_company: str | None = Field(default=None, max_length=255)
    submitted_date: DateString | None = None
    required_by_date: DateString | None = None
    reviewed_date: DateString | None = None
    status: SubmittalStatus = "Draft"
    reviewer: str | None = Field(default=None, max_length=255)
    remarks: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_date_order(
            self.submitted_date,
            self.required_by_date,
            self.reviewed_date,
        )
        return self


class SubmittalUpdate(BaseModel):
    specification_section: SpecificationSection | None = None
    title: SubmittalTitle | None = None
    responsible_company: str | None = Field(default=None, max_length=255)
    submitted_date: DateString | None = None
    required_by_date: DateString | None = None
    reviewed_date: DateString | None = None
    status: SubmittalStatus | None = None
    reviewer: str | None = Field(default=None, max_length=255)
    remarks: str | None = None

    @field_validator("specification_section", "title", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        validate_date_order(
            self.submitted_date,
            self.required_by_date,
            self.reviewed_date,
        )
        return self


class SubmittalResponse(ORMModel):
    id: int
    project_id: int
    number: str
    specification_section: str
    title: str
    responsible_company: str | None
    submitted_date: str | None
    required_by_date: str | None
    reviewed_date: str | None
    status: SubmittalStatus
    reviewer: str | None
    remarks: str | None
    created_at: datetime
    updated_at: datetime


class SubmittalListResponse(BaseModel):
    submittals: list[SubmittalResponse]
