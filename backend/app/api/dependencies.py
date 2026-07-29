from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import ATTACHMENT_CONFIG, AttachmentConfig
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.project import Project
from app.storage.attachment import (
    AttachmentStorage,
    AttachmentStorageConfigurationError,
)
from app.storage.factory import (
    build_attachment_storage,
    build_storage_resolver,
)

def get_owned_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Project:
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user["id"],
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    return project


def get_attachment_config() -> AttachmentConfig:
    return ATTACHMENT_CONFIG


def get_attachment_storage(
    config: AttachmentConfig = Depends(get_attachment_config),
) -> AttachmentStorage:
    try:
        return build_attachment_storage(config)
    except AttachmentStorageConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error


def get_attachment_storage_resolver(
    config: AttachmentConfig = Depends(get_attachment_config),
):
    return build_storage_resolver(config)
