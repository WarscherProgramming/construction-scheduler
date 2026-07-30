from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import MutationModel, ORMModel


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
