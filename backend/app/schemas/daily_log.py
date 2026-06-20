from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.task import DateString


class DailyLogCreate(BaseModel):
    date: DateString
    company: str = Field(min_length=1, max_length=255)
    manpower: int = Field(ge=0)
    work_performed: str | None = None
    delays: str | None = None
    notes: str | None = None


class DailyLogResponse(ORMModel):
    id: int
    project_id: int
    date: str
    company: str
    manpower: int
    work_performed: str | None
    delays: str | None
    notes: str | None


class DailyLogListResponse(BaseModel):
    daily_logs: list[DailyLogResponse]
