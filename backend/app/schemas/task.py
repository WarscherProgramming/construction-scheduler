from datetime import date, datetime
import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    StringConstraints,
    field_validator,
)

from app.schemas.common import MutationModel, ORMModel, UpdateMutationModel


def validate_date_string(value: str) -> str:
    date.fromisoformat(value)
    return value


DateString = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    AfterValidator(validate_date_string),
]
TaskName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
ProgressStatus = Literal["not_started", "in_progress", "completed"]


def normalize_predecessor(value: object) -> str:
    return str(value).replace(" ", "").upper()


PredecessorString = Annotated[
    str,
    BeforeValidator(normalize_predecessor),
    StringConstraints(
        pattern=r"^\d+(?:SS)?(?:\+\d+D?)?$",
        max_length=32,
    ),
]


PositiveTaskId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class TaskCreate(MutationModel):
    name: TaskName
    duration: int = Field(ge=1, le=36_500)
    predecessor: PredecessorString | None = None
    predecessor_task_id: PositiveTaskId | None = None
    dependency_type: Literal["FS", "SS"] = "FS"
    lag_days: int = Field(default=0, ge=0, le=36_500)
    manual_start_date: DateString | None = None
    parent_task_id: PositiveTaskId | None = None
    is_collapsed: int = Field(default=0, ge=0, le=1)


class TaskUpdate(UpdateMutationModel):
    name: TaskName | None = None
    duration: int | None = Field(default=None, ge=1, le=36_500)
    predecessor: PredecessorString | None = None
    predecessor_task_id: PositiveTaskId | None = None
    dependency_type: Literal["FS", "SS"] | None = None
    lag_days: int | None = Field(default=None, ge=0, le=36_500)
    manual_start_date: DateString | None = None
    parent_task_id: PositiveTaskId | None = None
    is_collapsed: int | None = Field(default=None, ge=0, le=1)

    @field_validator(
        "name",
        "duration",
        "dependency_type",
        "lag_days",
        "is_collapsed",
    )
    @classmethod
    def computational_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class TaskProgressUpdate(UpdateMutationModel):
    progress_status: ProgressStatus | None = None
    percent_complete: int | None = Field(default=None, ge=0, le=100)
    actual_start_date: DateString | None = None
    actual_finish_date: DateString | None = None
    remaining_duration: int | None = Field(
        default=None,
        ge=0,
        le=36_500,
    )


class TaskReorderRequest(MutationModel):
    task_ids: list[PositiveTaskId] = Field(min_length=1, max_length=2_000)


class TaskResponse(ORMModel):
    id: int
    name: str | None
    duration: int | None
    predecessor: str | None
    predecessor_task_id: int | None
    dependency_type: Literal["FS", "SS"]
    lag_days: int
    start_date: str | None
    end_date: str | None
    manual_start_date: str | None
    project_id: int
    order_index: int | None
    parent_task_id: int | None
    is_collapsed: int | None
    progress_status: ProgressStatus
    percent_complete: int
    actual_start_date: str | None
    actual_finish_date: str | None
    remaining_duration: int | None
    status_updated_at: datetime | None
    out_of_sequence: bool = False
    out_of_sequence_reason: str | None = None
    # Derived critical-path metadata, computed per response (not persisted).
    is_critical: bool = False
    total_float: int | None = None


class ScheduleProgressSummary(BaseModel):
    total_leaf_tasks: int
    not_started_count: int
    in_progress_count: int
    completed_count: int
    out_of_sequence_count: int
    percent_complete_weighted: float
    data_date: str
    forecast_project_finish: str | None
    completed_through_data_date: int
    tasks_started_last_7_days: int
    tasks_completed_last_7_days: int


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    summary: ScheduleProgressSummary


def parse_predecessor_reference(
    value: str | None,
) -> tuple[int | None, Literal["FS", "SS"], int]:
    if not value:
        return None, "FS", 0

    match = re.fullmatch(r"(\d+)(SS)?(?:\+(\d+)D?)?", value)
    if match is None:
        raise ValueError("Invalid predecessor reference")

    return (
        int(match.group(1)),
        "SS" if match.group(2) else "FS",
        int(match.group(3) or 0),
    )
