from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import (
    CollectionPage,
    PositiveId,
    get_collection_page,
    get_db,
    get_owned_project,
    get_storage_config,
    get_storage_provider,
    get_storage_provider_resolver,
)
from app.core.config import AttachmentConfig
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    FolderCreate,
    FolderListResponse,
    FolderResponse,
)
from app.services.document import (
    create_document,
    create_folder,
    document_content_disposition,
    get_owned_document,
    list_project_documents,
    list_project_folders,
    open_document_stream,
    soft_delete_document,
)
from app.storage.provider import StorageProvider


router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
)
def upload_document(
    project_id: int = Form(..., ge=1, le=2_147_483_647),
    folder_id: int | None = Form(
        default=None,
        ge=1,
        le=2_147_483_647,
    ),
    display_name: str | None = Form(default=None, max_length=255),
    document_type: str | None = Form(default=None, max_length=50),
    file: UploadFile = File(...),
    content_length: int | None = Header(
        default=None,
        alias="Content-Length",
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
    config: AttachmentConfig = Depends(get_storage_config),
):
    get_owned_project(project_id, db, current_user)
    return create_document(
        db,
        storage,
        config,
        project_id=project_id,
        folder_id=folder_id,
        upload=file,
        uploaded_by=current_user["id"],
        display_name=display_name,
        document_type=document_type,
        content_length=content_length,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_document_metadata(
    document_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_owned_document(db, document_id, current_user["id"])


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    storage_resolver=Depends(get_storage_provider_resolver),
    config: AttachmentConfig = Depends(get_storage_config),
):
    document = get_owned_document(db, document_id, current_user["id"])
    content = open_document_stream(
        storage_resolver,
        document,
        config.upload_chunk_size,
    )
    return StreamingResponse(
        content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": document_content_disposition(document),
            "Content-Length": str(document.size_bytes),
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/documents/{document_id}",
    response_model=MessageResponse,
)
def delete_document(
    document_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    soft_delete_document(db, document_id, current_user["id"])
    return {"message": "Document deleted"}


@router.get(
    "/projects/{project_id}/documents",
    response_model=DocumentListResponse,
)
def get_project_documents(
    project_id: int,
    folder_id: Annotated[
        int | None,
        Query(ge=1, le=2_147_483_647),
    ] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    page: CollectionPage = Depends(get_collection_page),
):
    return {
        "documents": list_project_documents(
            db,
            project_id,
            folder_id=folder_id,
            limit=page.limit,
            offset=page.offset,
        )
    }


@router.get(
    "/projects/{project_id}/folders",
    response_model=FolderListResponse,
)
def get_project_folders(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    page: CollectionPage = Depends(get_collection_page),
):
    return {
        "folders": list_project_folders(
            db,
            project_id,
            limit=page.limit,
            offset=page.offset,
        )
    }


@router.post(
    "/projects/{project_id}/folders",
    response_model=FolderResponse,
    status_code=201,
)
def add_project_folder(
    project_id: int,
    payload: FolderCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return create_folder(
        db,
        project_id=project_id,
        name=payload.name,
        parent_folder_id=payload.parent_folder_id,
        created_by=current_user["id"],
    )
