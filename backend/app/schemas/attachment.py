from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AttachmentResponse(ORMModel):
    id: int
    project_id: int
    parent_type: str
    parent_id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class AttachmentListResponse(BaseModel):
    attachments: list[AttachmentResponse]
