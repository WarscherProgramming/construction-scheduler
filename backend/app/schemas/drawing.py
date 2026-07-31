from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.schemas.common import (
    MAX_LONG_TEXT_LENGTH,
    MutationModel,
    UpdateMutationModel,
)
from app.schemas.task import DateString


DrawingSetStatus = Literal["draft", "active", "archived"]
DrawingSheetStatus = Literal["active", "void", "archived"]
DrawingIssueStatus = Literal["draft", "issued", "void"]
DrawingIssuePurpose = Literal[
    "bid",
    "permit",
    "construction",
    "addendum",
    "bulletin",
    "record",
    "as_built",
    "other",
]
DrawingDiscipline = Literal[
    "G",
    "C",
    "L",
    "A",
    "I",
    "S",
    "M",
    "P",
    "FP",
    "E",
    "T",
    "FA",
    "K",
    "Q",
    "V",
    "X",
]
RequiredName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
SheetNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
SheetTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
RevisionCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
OptionalDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_LONG_TEXT_LENGTH),
]
PositiveId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class DrawingSetCreate(MutationModel):
    name: RequiredName
    description: OptionalDescription | None = None
    status: DrawingSetStatus = "draft"
    issue_date: DateString | None = None


class DrawingSetUpdate(UpdateMutationModel):
    name: RequiredName | None = None
    description: OptionalDescription | None = None
    status: Literal["draft", "active"] | None = None
    issue_date: DateString | None = None

    @field_validator("name", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class DrawingSheetCreateMetadata(MutationModel):
    sheet_number: SheetNumber
    title: SheetTitle
    discipline: DrawingDiscipline
    description: OptionalDescription | None = None
    revision_code: RevisionCode
    revision_date: DateString
    revision_description: OptionalDescription | None = None


class DrawingSheetUpdate(UpdateMutationModel):
    sheet_number: SheetNumber | None = None
    title: SheetTitle | None = None
    discipline: DrawingDiscipline | None = None
    description: OptionalDescription | None = None
    status: DrawingSheetStatus | None = None

    @field_validator("sheet_number", "title", "discipline", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class DrawingRevisionCreateMetadata(MutationModel):
    revision_code: RevisionCode
    revision_date: DateString
    description: OptionalDescription | None = None


class DrawingIssueCreate(MutationModel):
    name: RequiredName
    issue_number: SheetNumber
    issue_date: DateString
    purpose: DrawingIssuePurpose
    notes: OptionalDescription | None = None


class DrawingIssueUpdate(UpdateMutationModel):
    name: RequiredName | None = None
    issue_number: SheetNumber | None = None
    issue_date: DateString | None = None
    purpose: DrawingIssuePurpose | None = None
    notes: OptionalDescription | None = None

    @field_validator(
        "name",
        "issue_number",
        "issue_date",
        "purpose",
    )
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class DrawingIssueMembershipCreate(MutationModel):
    revision_id: PositiveId


class DrawingSetResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    status: DrawingSetStatus
    issue_date: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    sheet_count: int = 0
    issue_count: int = 0


class DrawingRevisionResponse(BaseModel):
    id: int
    project_id: int
    drawing_sheet_id: int
    document_id: int
    revision_code: str
    revision_date: str
    description: str | None
    sequence_number: int
    is_current: bool
    superseded_at: datetime | None
    superseded_by_revision_id: int | None
    original_filename: str
    size_bytes: int
    created_at: datetime
    issue_ids: list[int] = Field(default_factory=list)


class DrawingSheetResponse(BaseModel):
    id: int
    project_id: int
    drawing_set_id: int
    drawing_set_name: str
    sheet_number: str
    title: str
    discipline: DrawingDiscipline
    description: str | None
    status: DrawingSheetStatus
    current_revision_id: int | None
    current_revision: DrawingRevisionResponse | None
    revision_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DrawingIssueRevisionResponse(BaseModel):
    revision_id: int
    sheet_id: int
    sheet_number: str
    sheet_title: str
    revision_code: str
    revision_date: str
    is_current: bool


class DrawingIssueResponse(BaseModel):
    id: int
    project_id: int
    drawing_set_id: int
    drawing_set_name: str
    name: str
    issue_number: str
    issue_date: str
    purpose: DrawingIssuePurpose
    status: DrawingIssueStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    issued_at: datetime | None
    deleted_at: datetime | None
    revisions: list[DrawingIssueRevisionResponse]


class DrawingRegisterPagination(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class DrawingRegisterResponse(BaseModel):
    project_id: int
    sheets: list[DrawingSheetResponse]
    pagination: DrawingRegisterPagination


class DrawingSetListResponse(BaseModel):
    drawing_sets: list[DrawingSetResponse]


class DrawingSheetListResponse(BaseModel):
    sheets: list[DrawingSheetResponse]


class DrawingRevisionListResponse(BaseModel):
    revisions: list[DrawingRevisionResponse]


class DrawingIssueListResponse(BaseModel):
    issues: list[DrawingIssueResponse]
