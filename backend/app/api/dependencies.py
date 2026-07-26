from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import ATTACHMENT_CONFIG, AttachmentConfig
from app.core.security import get_current_user
from app.db.database import SessionLocal
from app.models.project import Project
from app.storage.attachment import (
    AttachmentStorage,
    LocalAttachmentStorage,
    MemoryAttachmentStorage,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@lru_cache(maxsize=4)
def build_attachment_storage(
    provider: str,
    local_root: str,
) -> AttachmentStorage:
    if provider == "local":
        return LocalAttachmentStorage(Path(local_root))
    if provider == "memory":
        return MemoryAttachmentStorage()

    raise ValueError("Unsupported attachment storage provider")


def get_attachment_storage(
    config: AttachmentConfig = Depends(get_attachment_config),
) -> AttachmentStorage:
    try:
        return build_attachment_storage(
            config.storage_provider,
            str(config.local_storage_root),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error
