from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.task import DateString


class InspectionCreate(BaseModel):
    date: DateString
    inspection_type: str = Field(min_length=1, max_length=255)
    inspector: str | None = Field(default=None, max_length=255)
    status: str = Field(min_length=1, max_length=100)
    notes: str | None = None
    corrective_action: str | None = None


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
