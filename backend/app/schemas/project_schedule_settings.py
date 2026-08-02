from datetime import datetime

from app.schemas.common import MutationModel, ORMModel
from app.schemas.task import DateString


class ProjectScheduleSettingsUpdate(MutationModel):
    schedule_start_date: DateString


class ProjectScheduleSettingsResponse(ORMModel):
    project_id: int
    schedule_start_date: str
    comparison_baseline_id: int | None
    created_at: datetime
    updated_at: datetime
