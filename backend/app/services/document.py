from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from hashlib import sha256
import logging
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.document import Document
from app.models.folder import Folder
from app.models.project import Project
from app.services.attachment import (
    FILE_RULES,
    MULTIPART_OVERHEAD_ALLOWANCE,
    validate_file_signature,
    validated_file_rule,
)
from app.services.attachment_cleanup import enqueue_cleanup_job
from app.storage.provider import (
    StorageObjectMissing,
    StorageProvider,
    StorageProviderError,
    StorageStreamTooLarge,
)


logger = logging.getLogger(__name__)
MAX_FILENAME_LENGTH = 255
MAX_EXTENSION_LENGTH = 20
MAX_DISPLAY_NAME_LENGTH = 255
MAX_DOCUMENT_TYPE_LENGTH = 50
RESERVED_FILENAME_STEMS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
StorageResolver = Callable[[str], StorageProvider]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_document_filename(filename: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(filename or "")).strip()
    if (
        not normalized
        or len(normalized) > MAX_FILENAME_LENGTH
        or "/" in normalized
        or "\\" in normalized
        or normalized in {".", ".."}
        or normalized[-1] in {" ", "."}
        or any(
            character == "\x00"
            or unicodedata.category(character).startswith("C")
            for character in normalized
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid document filename is required",
        )

    extension = Path(normalized).suffix.lower()
    if not extension or len(extension) > MAX_EXTENSION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid document file extension is required",
        )
    if extension not in FILE_RULES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document file extension",
        )

    stem = normalized[: -len(extension)]
    if (
        not stem
        or stem.upper() in RESERVED_FILENAME_STEMS
        or stem.rstrip(" .") != stem
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid document filename is required",
        )
    return normalized


def normalize_metadata_text(
    value: str | None,
    *,
    field_name: str,
    maximum: int,
    fallback: str | None = None,
) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not normalized and fallback is not None:
        normalized = fallback
    if (
        not normalized
        or len(normalized) > maximum
        or any(
            character == "\x00"
            or unicodedata.category(character).startswith("C")
            for character in normalized
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"A valid {field_name} is required",
        )
    return normalized


def normalize_folder_name(name: str) -> str:
    normalized = normalize_metadata_text(
        name,
        field_name="folder name",
        maximum=255,
    )
    if (
        normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or normalized[-1] in {" ", "."}
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid folder name is required",
        )
    return normalized


def generate_document_storage_key() -> str:
    identifier = uuid.uuid4().hex
    return f"documents/{identifier[:2]}/{identifier[2:4]}/{identifier}"


def get_project_folder(
    db: Session,
    project_id: int,
    folder_id: int,
) -> Folder:
    folder = (
        db.query(Folder)
        .filter(
            Folder.id == folder_id,
            Folder.project_id == project_id,
            Folder.deleted_at.is_(None),
        )
        .first()
    )
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    return folder


def _validate_folder_ancestry(
    db: Session,
    project_id: int,
    parent: Folder,
) -> None:
    seen: set[int] = set()
    current = parent
    while current is not None:
        if current.id in seen:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Folder hierarchy contains a cycle",
            )
        seen.add(current.id)
        if current.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )
        if current.parent_folder_id is None:
            return
        current = (
            db.query(Folder)
            .filter(
                Folder.id == current.parent_folder_id,
                Folder.project_id == project_id,
                Folder.deleted_at.is_(None),
            )
            .first()
        )
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Folder hierarchy contains an invalid parent",
            )


def create_folder(
    db: Session,
    *,
    project_id: int,
    name: str,
    parent_folder_id: int | None,
    created_by: int,
) -> Folder:
    normalized_name = normalize_folder_name(name)
    parent = None
    if parent_folder_id is not None:
        parent = get_project_folder(db, project_id, parent_folder_id)
        _validate_folder_ancestry(db, project_id, parent)

    folder = Folder(
        project_id=project_id,
        parent_folder_id=parent_folder_id,
        name=normalized_name,
        path=f"pending/{uuid.uuid4().hex}",
        created_by=created_by,
    )
    db.add(folder)
    try:
        db.flush()
        folder.path = (
            f"{parent.path}/{folder.id}"
            if parent is not None
            else f"/{folder.id}"
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A folder with this name already exists here",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create folder",
        ) from error

    db.refresh(folder)
    return folder


def list_project_folders(
    db: Session,
    project_id: int,
    *,
    limit: int,
    offset: int,
) -> list[Folder]:
    return (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.deleted_at.is_(None),
        )
        .order_by(Folder.path.asc(), Folder.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def create_document(
    db: Session,
    storage: StorageProvider,
    config: AttachmentConfig,
    *,
    project_id: int,
    folder_id: int | None,
    upload: UploadFile,
    uploaded_by: int,
    display_name: str | None,
    document_type: str | None,
    content_length: int | None,
) -> Document:
    folder = (
        get_project_folder(db, project_id, folder_id)
        if folder_id is not None
        else None
    )
    filename = normalize_document_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    mime_type, rule = validated_file_rule(
        filename,
        upload.content_type,
        config,
        resource_name="Document",
    )
    normalized_display_name = normalize_metadata_text(
        display_name,
        field_name="document display name",
        maximum=MAX_DISPLAY_NAME_LENGTH,
        fallback=filename[: -len(extension)],
    )
    normalized_document_type = normalize_metadata_text(
        document_type,
        field_name="document type",
        maximum=MAX_DOCUMENT_TYPE_LENGTH,
        fallback="General",
    )

    if (
        content_length is not None
        and content_length
        > config.max_upload_size + MULTIPART_OVERHEAD_ALLOWANCE
    ):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Document exceeds the maximum upload size",
        )
    if upload.size is not None and upload.size > config.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Document exceeds the maximum upload size",
        )

    upload.file.seek(0)
    first_chunk = upload.file.read(max(config.upload_chunk_size, 512))
    if not first_chunk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Empty documents are not allowed",
        )
    validate_file_signature(
        first_chunk,
        rule,
        resource_name="Document",
    )

    digest = sha256()
    size_bytes = 0

    def upload_chunks() -> Iterator[bytes]:
        nonlocal size_bytes
        chunk = first_chunk
        while chunk:
            size_bytes += len(chunk)
            if size_bytes > config.max_upload_size:
                raise StorageStreamTooLarge(
                    "Document exceeds the maximum upload size"
                )
            digest.update(chunk)
            yield chunk
            chunk = upload.file.read(config.upload_chunk_size)

    storage_key = generate_document_storage_key()
    try:
        storage.upload(
            storage_key,
            upload_chunks(),
            content_type=mime_type,
        )
    except StorageStreamTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Document exceeds the maximum upload size",
        ) from error
    except StorageProviderError as error:
        logger.exception(
            "Document upload failed for provider %s",
            storage.provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is unavailable",
        ) from error

    document = Document(
        project_id=project_id,
        folder_id=folder.id if folder is not None else None,
        parent_document_id=None,
        original_filename=filename,
        display_name=normalized_display_name,
        extension=extension,
        mime_type=mime_type,
        size_bytes=size_bytes,
        checksum_sha256=digest.hexdigest(),
        storage_provider=storage.provider_name,
        storage_key=storage_key,
        storage_bucket=(
            config.s3_bucket if storage.provider_name == "s3" else None
        ),
        uploaded_by=uploaded_by,
        version=1,
        is_current_version=True,
        document_type=normalized_document_type,
        status="Active",
    )
    db.add(document)

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        _cleanup_failed_document_upload(
            db,
            storage,
            project_id,
            storage_key,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save document metadata",
        ) from error

    db.refresh(document)
    return document


def _cleanup_failed_document_upload(
    db: Session,
    storage: StorageProvider,
    project_id: int,
    storage_key: str,
) -> None:
    cleanup_category = "unknown"
    try:
        storage.delete(storage_key)
        return
    except StorageProviderError as cleanup_error:
        cleanup_category = cleanup_error.category
        logger.exception(
            "Document metadata failed and storage cleanup also failed for "
            "provider %s",
            storage.provider_name,
        )

    try:
        job = enqueue_cleanup_job(
            db,
            attachment_id=None,
            project_id=project_id,
            storage_provider=storage.provider_name,
            storage_key=storage_key,
        )
        job.last_error = (
            f"{cleanup_category}: document storage operation failed"
        )[:500]
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.critical(
            "Unable to persist document upload rollback cleanup for "
            "provider %s",
            storage.provider_name,
            exc_info=True,
        )


def list_project_documents(
    db: Session,
    project_id: int,
    *,
    folder_id: int | None,
    limit: int,
    offset: int,
) -> list[Document]:
    if folder_id is not None:
        get_project_folder(db, project_id, folder_id)

    query = db.query(Document).filter(
        Document.project_id == project_id,
        Document.deleted_at.is_(None),
    )
    if folder_id is not None:
        query = query.filter(Document.folder_id == folder_id)
    return (
        query.order_by(Document.created_at.asc(), Document.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_owned_document(
    db: Session,
    document_id: int,
    user_id: int,
    *,
    include_deleted: bool = False,
) -> Document:
    query = (
        db.query(Document)
        .join(Project, Project.id == Document.project_id)
        .filter(
            Document.id == document_id,
            Project.user_id == user_id,
        )
    )
    if not include_deleted:
        query = query.filter(Document.deleted_at.is_(None))
    document = query.first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def open_document_stream(
    resolver: StorageResolver,
    document: Document,
    chunk_size: int,
) -> Iterator[bytes]:
    try:
        storage = resolver(document.storage_provider)
        return storage.download(document.storage_key, chunk_size)
    except StorageObjectMissing as error:
        logger.error("Stored content is missing for document %s", document.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document content is unavailable",
        ) from error
    except StorageProviderError as error:
        logger.exception(
            "Document provider failed while opening document %s",
            document.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is unavailable",
        ) from error


def document_content_disposition(document: Document) -> str:
    rule = FILE_RULES[document.extension]
    disposition = "inline" if rule.inline else "attachment"
    fallback = "".join(
        character
        if 32 <= ord(character) < 127
        and character not in {'"', "\\", ";"}
        else "_"
        for character in document.original_filename
    )
    encoded = quote(document.original_filename, safe="")
    return (
        f'{disposition}; filename="{fallback}"; '
        f"filename*=UTF-8''{encoded}"
    )


def soft_delete_document(
    db: Session,
    document_id: int,
    user_id: int,
) -> Document:
    document = get_owned_document(
        db,
        document_id,
        user_id,
        include_deleted=True,
    )
    if document.deleted_at is not None:
        return document

    document.deleted_at = utc_now()
    document.is_current_version = False
    document.status = "Deleted"
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete document",
        ) from error
    db.refresh(document)
    return document
