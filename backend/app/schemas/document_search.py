from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import MutationModel


ExtractionStatus = Literal[
    "pending",
    "processing",
    "completed",
    "completed_with_warnings",
    "failed",
    "unavailable",
    "cancelled",
]
ExtractionMethod = Literal[
    "embedded_text",
    "ocr",
    "mixed",
    "metadata_only",
    "unavailable",
]


class DocumentExtractionSummaryResponse(BaseModel):
    status: ExtractionStatus
    extraction_method: ExtractionMethod
    page_count: int = Field(ge=0)
    pages_processed: int = Field(ge=0)
    text_character_count: int = Field(ge=0)
    searchable: bool
    language: str
    warning_codes: list[str]
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    failure_code: str | None
    failure_message: str | None
    extractor_version: str
    source_current: bool
    job_status: Literal["pending", "processing"] | None
    retry_eligible: bool


class DocumentExtractionStatusResponse(BaseModel):
    project_id: int
    document_id: int
    extraction: DocumentExtractionSummaryResponse


class DocumentExtractionReprocessRequest(MutationModel):
    pass


class SearchMatchRange(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class SearchRouteTarget(BaseModel):
    type: Literal["document", "drawing_revision"]
    document_id: int
    drawing_sheet_id: int | None = None
    drawing_revision_id: int | None = None


class DocumentSearchResult(BaseModel):
    result_type: Literal["document", "drawing_revision"]
    document_id: int
    drawing_revision_id: int | None
    drawing_sheet_id: int | None
    drawing_set_id: int | None
    display_name: str
    document_type: str
    sheet_number: str | None
    sheet_title: str | None
    discipline: str | None
    revision_code: str | None
    revision_status: Literal["current", "superseded"] | None
    page_number: int | None
    snippet: str
    match_ranges: list[SearchMatchRange]
    rank: float = Field(ge=0)
    extraction_method: ExtractionMethod
    updated_at: datetime
    route_target: SearchRouteTarget


class DocumentSearchPagination(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class DocumentSearchResponse(BaseModel):
    project_id: int
    query: str
    scope: Literal["all", "documents", "drawings"]
    results: list[DocumentSearchResult]
    pagination: DocumentSearchPagination
