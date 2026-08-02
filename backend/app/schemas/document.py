from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import MutationModel, ORMModel
from app.schemas.document_search import DocumentExtractionSummaryResponse


class FolderCreate(MutationModel):
    name: str = Field(min_length=1, max_length=255)
    parent_folder_id: int | None = Field(
        default=None,
        ge=1,
        le=2_147_483_647,
    )


class FolderResponse(ORMModel):
    id: int
    project_id: int
    parent_folder_id: int | None
    name: str
    path: str
    created_at: datetime
    updated_at: datetime


class FolderListResponse(BaseModel):
    folders: list[FolderResponse]


class DocumentResponse(ORMModel):
    id: int
    project_id: int
    folder_id: int | None
    parent_document_id: int | None
    original_filename: str
    display_name: str
    extension: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    uploaded_by: int
    created_at: datetime
    updated_at: datetime
    version: int
    is_current_version: bool
    document_type: str
    status: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class ExplorerFolderResponse(BaseModel):
    id: int
    name: str
    parent_folder_id: int | None
    created_at: datetime
    updated_at: datetime
    child_folder_count: int
    document_count: int


class BreadcrumbResponse(BaseModel):
    id: int
    name: str


class ExplorerDocumentResponse(BaseModel):
    id: int
    folder_id: int | None
    display_name: str
    original_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    document_type: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    extraction: DocumentExtractionSummaryResponse | None = None


class ExplorerPaginationResponse(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class DocumentExplorerResponse(BaseModel):
    project_id: int
    current_folder: ExplorerFolderResponse | None
    breadcrumbs: list[BreadcrumbResponse]
    folders: list[ExplorerFolderResponse]
    documents: list[ExplorerDocumentResponse]
    pagination: ExplorerPaginationResponse


class FolderTreeResponse(BaseModel):
    folders: list[ExplorerFolderResponse]


class RecentDocumentsResponse(BaseModel):
    documents: list[ExplorerDocumentResponse]
