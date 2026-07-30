from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import MAX_LONG_TEXT_LENGTH, MutationModel, ORMModel
from app.schemas.task import DateString


class InspectionCreate(MutationModel):
    date: DateString
    inspection_type: str = Field(min_length=1, max_length=255)
    inspector: str | None = Field(default=None, max_length=255)
    status: Literal["Pending", "Pass", "Partial Pass", "Fail"]
    notes: str | None = Field(default=None, max_length=MAX_LONG_TEXT_LENGTH)
    corrective_action: str | None = Field(
        default=None, max_length=MAX_LONG_TEXT_LENGTH
    )


class InspectionResponse(ORMModel):
    id: int
    project_id: int
    date: str
    inspection_type: str
    inspector: str | None
    status: str
    notes: str | None
    corrective_action: str | None


class InspectionListResponse(BaseModel):
    inspections: list[InspectionResponse]
