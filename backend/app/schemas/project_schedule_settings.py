from datetime import datetime

from app.schemas.common import MutationModel, ORMModel
from app.schemas.task import DateString


class ProjectScheduleSettingsUpdate(MutationModel):
    schedule_start_date: DateString


class ProjectScheduleSettingsResponse(ORMModel):
    project_id: int
    schedule_start_date: str
    created_at: datetime
    updated_at: datetime
