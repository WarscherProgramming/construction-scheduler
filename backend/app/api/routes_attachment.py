from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_attachment_config,
    get_attachment_storage,
    get_db,
    get_owned_project,
)
from app.core.config import AttachmentConfig
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.attachment import (
    AttachmentListResponse,
    AttachmentResponse,
)
from app.schemas.common import MessageResponse
from app.services.attachment import (
    content_disposition,
    create_attachment,
    delete_attachment,
    get_project_attachment,
    list_attachment_records,
    open_attachment_stream,
)
from app.storage.attachment import AttachmentStorage


router = APIRouter()


@router.get(
    "/projects/{project_id}/attachments",
    response_model=AttachmentListResponse,
)
def get_attachments(
    project_id: int,
    parent_type: str,
    parent_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {
        "attachments": list_attachment_records(
            db,
            project_id,
            parent_type,
            parent_id,
        )
    }


@router.post(
    "/projects/{project_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
)
def upload_attachment(
    project_id: int,
    parent_type: str = Form(...),
    parent_id: int = Form(...),
    file: UploadFile = File(...),
    content_length: int | None = Header(
        default=None,
        alias="Content-Length",
        ge=0,
    ),
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    storage: AttachmentStorage = Depends(get_attachment_storage),
    config: AttachmentConfig = Depends(get_attachment_config),
):
    return create_attachment(
        db,
        storage,
        config,
        project_id=project_id,
        parent_type=parent_type,
        parent_id=parent_id,
        upload=file,
        uploaded_by=current_user["id"],
        content_length=content_length,
    )


@router.get(
    "/projects/{project_id}/attachments/{attachment_id}/download",
)
def download_attachment(
    project_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    storage: AttachmentStorage = Depends(get_attachment_storage),
    config: AttachmentConfig = Depends(get_attachment_config),
):
    attachment = get_project_attachment(db, project_id, attachment_id)
    content = open_attachment_stream(
        storage,
        attachment,
        config.upload_chunk_size,
    )
    return StreamingResponse(
        content,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": content_disposition(attachment),
            "Content-Length": str(attachment.size_bytes),
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/projects/{project_id}/attachments/{attachment_id}",
    response_model=MessageResponse,
)
def remove_attachment(
    project_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    storage: AttachmentStorage = Depends(get_attachment_storage),
    config: AttachmentConfig = Depends(get_attachment_config),
):
    attachment = get_project_attachment(db, project_id, attachment_id)
    delete_attachment(db, storage, config, attachment)
    return {"message": "Attachment deleted"}
