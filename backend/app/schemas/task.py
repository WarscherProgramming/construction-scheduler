from datetime import date
from typing import Annotated

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
    name: str = Field(min_length=1, max_length=500)
    duration: int = Field(ge=1)
    predecessor: PredecessorString | None = None
    manual_start_date: DateString | None = None
    order_index: int | None = Field(default=None, ge=0)
    parent_task_id: int | None = Field(default=None, ge=1)
    indent_level: int = Field(default=0, ge=0)
    is_collapsed: int = Field(default=0, ge=0, le=1)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    duration: int | None = Field(default=None, ge=1)
    predecessor: PredecessorString | None = None
    manual_start_date: DateString | None = None
    order_index: int | None = Field(default=None, ge=0)
    parent_task_id: int | None = Field(default=None, ge=1)
    indent_level: int | None = Field(default=None, ge=0)
    is_collapsed: int | None = Field(default=None, ge=0, le=1)


class TaskReorderRequest(BaseModel):
    task_ids: list[int] = Field(min_length=1)


class TaskResponse(ORMModel):
    id: int
    name: str | None
    duration: int | None
    predecessor: str | None
    start_date: str | None
    end_date: str | None
    manual_start_date: str | None
    project_id: int
    order_index: int | None
    parent_task_id: int | None
    indent_level: int | None
    is_collapsed: int | None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
