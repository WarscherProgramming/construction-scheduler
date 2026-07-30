from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import MAX_LONG_TEXT_LENGTH, MutationModel, ORMModel
from app.schemas.task import DateString


class NoteDelayCreate(MutationModel):
    date: DateString
    entry_type: Literal["Note", "Delay"]
    company: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=1, max_length=MAX_LONG_TEXT_LENGTH)
    impact: str | None = Field(default=None, max_length=MAX_LONG_TEXT_LENGTH)


class NoteDelayResponse(ORMModel):
    id: int
    project_id: int
    date: str
    entry_type: str
    company: str | None
    description: str
    impact: str | None


class NoteDelayListResponse(BaseModel):
    notes_delays: list[NoteDelayResponse]
