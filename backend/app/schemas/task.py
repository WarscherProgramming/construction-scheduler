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
    model_validator,
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
DependencyType = Literal["FS", "SS", "FF", "SF"]
ConstraintType = Literal[
    "ASAP",
    "ALAP",
    "SNET",
    "SNLT",
    "FNET",
    "FNLT",
    "MS",
    "MF",
]


def normalize_predecessor(value: object) -> str:
    return str(value).replace(" ", "").upper()


PredecessorString = Annotated[
    str,
    BeforeValidator(normalize_predecessor),
    StringConstraints(
        pattern=r"^\d+(?:(?:FS|SS|FF|SF))?(?:[+-]\d+D?)?$",
        max_length=32,
    ),
]


PositiveTaskId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class TaskDependencyInput(MutationModel):
    predecessor_task_id: PositiveTaskId
    dependency_type: DependencyType = "FS"
    lag_days: int = Field(default=0, ge=-36_500, le=36_500)


class TaskDependencyResponse(ORMModel):
    id: int
    predecessor_task_id: int
    dependency_type: DependencyType
    lag_days: int


class TaskCreate(MutationModel):
    name: TaskName
    duration: int = Field(ge=0, le=36_500)
    predecessor: PredecessorString | None = None
    predecessor_task_id: PositiveTaskId | None = None
    dependency_type: DependencyType = "FS"
    lag_days: int = Field(default=0, ge=-36_500, le=36_500)
    dependencies: list[TaskDependencyInput] = Field(
        default_factory=list,
        max_length=50,
    )
    manual_start_date: DateString | None = None
    parent_task_id: PositiveTaskId | None = None
    is_collapsed: int = Field(default=0, ge=0, le=1)
    is_milestone: bool = False
    constraint_type: ConstraintType = "ASAP"
    constraint_date: DateString | None = None

    @model_validator(mode="after")
    def validate_planning_fields(self):
        if self.is_milestone and self.duration != 0:
            raise ValueError("Milestones must have zero duration")
        if not self.is_milestone and self.duration < 1:
            raise ValueError("Non-milestone tasks require a duration")
        _validate_constraint_pair(self.constraint_type, self.constraint_date)
        return self


class TaskUpdate(UpdateMutationModel):
    name: TaskName | None = None
    duration: int | None = Field(default=None, ge=0, le=36_500)
    predecessor: PredecessorString | None = None
    predecessor_task_id: PositiveTaskId | None = None
    dependency_type: DependencyType | None = None
    lag_days: int | None = Field(default=None, ge=-36_500, le=36_500)
    dependencies: list[TaskDependencyInput] | None = Field(
        default=None,
        max_length=50,
    )
    manual_start_date: DateString | None = None
    parent_task_id: PositiveTaskId | None = None
    is_collapsed: int | None = Field(default=None, ge=0, le=1)
    is_milestone: bool | None = None
    constraint_type: ConstraintType | None = None
    constraint_date: DateString | None = None

    @field_validator(
        "name",
        "duration",
        "dependency_type",
        "lag_days",
        "is_collapsed",
        "is_milestone",
        "constraint_type",
        "dependencies",
    )
    @classmethod
    def computational_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_planning_fields(self):
        if self.is_milestone is True and self.duration not in (None, 0):
            raise ValueError("Milestones must have zero duration")
        if self.is_milestone is False and self.duration == 0:
            raise ValueError("Non-milestone tasks require a duration")
        if self.constraint_type is not None:
            _validate_constraint_pair(
                self.constraint_type,
                self.constraint_date,
                allow_omitted_date="constraint_date" not in self.model_fields_set,
            )
        return self


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
    dependency_type: DependencyType
    lag_days: int
    dependencies: list[TaskDependencyResponse]
    start_date: str | None
    end_date: str | None
    manual_start_date: str | None
    is_milestone: bool
    constraint_type: ConstraintType
    constraint_date: str | None
    constraint_violated: bool = False
    constraint_violation_reason: str | None = None
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
) -> tuple[int | None, DependencyType, int]:
    if not value:
        return None, "FS", 0

    match = re.fullmatch(
        r"(\d+)(FS|SS|FF|SF)?(?:([+-])(\d+)D?)?",
        value,
    )
    if match is None:
        raise ValueError("Invalid predecessor reference")

    return (
        int(match.group(1)),
        match.group(2) or "FS",
        (-1 if match.group(3) == "-" else 1) * int(match.group(4) or 0),
    )


def _validate_constraint_pair(
    constraint_type: ConstraintType,
    constraint_date: str | None,
    *,
    allow_omitted_date: bool = False,
) -> None:
    if constraint_type in ("ASAP", "ALAP"):
        if constraint_date is not None:
            raise ValueError(
                f"{constraint_type} constraints cannot have a constraint date"
            )
        return
    if constraint_date is None and not allow_omitted_date:
        raise ValueError(f"{constraint_type} requires a constraint date")
