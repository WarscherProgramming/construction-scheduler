from datetime import date
import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    StringConstraints,
)

from app.schemas.common import ORMModel


def validate_date_string(value: str) -> str:
    date.fromisoformat(value)
    return value


DateString = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    AfterValidator(validate_date_string),
]
TaskName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


def normalize_predecessor(value: object) -> str:
    return str(value).replace(" ", "").upper()


PredecessorString = Annotated[
    str,
    BeforeValidator(normalize_predecessor),
    StringConstraints(
        pattern=r"^\d+(?:SS)?(?:\+\d+D?)?$",
    ),
]


class TaskCreate(BaseModel):
    name: TaskName
    duration: int = Field(ge=1)
    predecessor: PredecessorString | None = None
    predecessor_task_id: int | None = Field(default=None, ge=1)
    dependency_type: Literal["FS", "SS"] = "FS"
    lag_days: int = Field(default=0, ge=0)
    manual_start_date: DateString | None = None
    order_index: int | None = Field(default=None, ge=0)
    parent_task_id: int | None = Field(default=None, ge=1)
    is_collapsed: int = Field(default=0, ge=0, le=1)


class TaskUpdate(BaseModel):
    name: TaskName | None = None
    duration: int | None = Field(default=None, ge=1)
    predecessor: PredecessorString | None = None
    predecessor_task_id: int | None = Field(default=None, ge=1)
    dependency_type: Literal["FS", "SS"] | None = None
    lag_days: int | None = Field(default=None, ge=0)
    manual_start_date: DateString | None = None
    order_index: int | None = Field(default=None, ge=0)
    parent_task_id: int | None = Field(default=None, ge=1)
    is_collapsed: int | None = Field(default=None, ge=0, le=1)


class TaskReorderRequest(BaseModel):
    task_ids: list[int] = Field(min_length=1)


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
    # Derived critical-path metadata, computed per response (not persisted).
    is_critical: bool = False
    total_float: int | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


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
