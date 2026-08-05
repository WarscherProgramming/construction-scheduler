from datetime import datetime

from pydantic import field_validator

from app.schemas.common import ORMModel, UpdateMutationModel
from app.schemas.task import DateString


class ProjectScheduleSettingsUpdate(UpdateMutationModel):
    schedule_start_date: DateString | None = None
    data_date: DateString | None = None

    @field_validator("schedule_start_date", "data_date")
    @classmethod
    def schedule_dates_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class ProjectScheduleSettingsResponse(ORMModel):
    project_id: int
    schedule_start_date: str
    data_date: str
    comparison_baseline_id: int | None
    created_at: datetime
    updated_at: datetime
