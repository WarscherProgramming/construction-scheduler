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
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    DOCUMENT_EXTRACTION_CONFIG,
    AttachmentConfig,
    DocumentExtractionConfig,
)
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
from app.services.document_extraction import (
    cancel_document_extraction,
    enqueue_document_extraction,
    get_document_extraction_summaries,
)
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
MAX_FOLDER_TREE_ITEMS = 500
MAX_FOLDER_DEPTH = 32
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
    commit: bool = True,
    extraction_config: DocumentExtractionConfig = DOCUMENT_EXTRACTION_CONFIG,
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
        db.flush()
        enqueue_document_extraction(
            db,
            document,
            uploaded_by,
            extraction_config,
        )
        if commit:
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

    if commit:
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


def _active_document_query(db: Session, project_id: int):
    return (
        db.query(Document)
        .outerjoin(Folder, Folder.id == Document.folder_id)
        .filter(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.is_current_version.is_(True),
            or_(
                Document.folder_id.is_(None),
                Folder.deleted_at.is_(None),
            ),
        )
    )


def _folder_count_maps(
    db: Session,
    project_id: int,
) -> tuple[dict[int, int], dict[int, int]]:
    child_counts = {
        parent_id: count
        for parent_id, count in (
            db.query(
                Folder.parent_folder_id,
                func.count(Folder.id),
            )
            .filter(
                Folder.project_id == project_id,
                Folder.deleted_at.is_(None),
                Folder.parent_folder_id.is_not(None),
            )
            .group_by(Folder.parent_folder_id)
            .all()
        )
    }
    document_counts = {
        folder_id: count
        for folder_id, count in (
            db.query(
                Document.folder_id,
                func.count(Document.id),
            )
            .join(Folder, Folder.id == Document.folder_id)
            .filter(
                Document.project_id == project_id,
                Document.deleted_at.is_(None),
                Document.is_current_version.is_(True),
                Folder.deleted_at.is_(None),
            )
            .group_by(Document.folder_id)
            .all()
        )
    }
    return child_counts, document_counts


def _folder_response(
    folder: Folder,
    child_counts: dict[int, int],
    document_counts: dict[int, int],
) -> dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_folder_id": folder.parent_folder_id,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "child_folder_count": child_counts.get(folder.id, 0),
        "document_count": document_counts.get(folder.id, 0),
    }


def _document_response(
    document: Document,
    extraction: dict | None = None,
) -> dict:
    response = {
        "id": document.id,
        "folder_id": document.folder_id,
        "display_name": document.display_name,
        "original_filename": document.original_filename,
        "extension": document.extension,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "document_type": document.document_type,
        "status": document.status,
        "version": document.version,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }
    if extraction is not None:
        response["extraction"] = extraction
    return response


def _folder_breadcrumbs(
    db: Session,
    project_id: int,
    current_folder: Folder | None,
) -> list[dict]:
    if current_folder is None:
        return []

    folder_ids = [
        int(value)
        for value in current_folder.path.strip("/").split("/")
        if value
    ]
    if (
        not folder_ids
        or len(folder_ids) > MAX_FOLDER_DEPTH
        or folder_ids[-1] != current_folder.id
        or len(set(folder_ids)) != len(folder_ids)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder hierarchy is invalid",
        )

    folders = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.id.in_(folder_ids),
            Folder.deleted_at.is_(None),
        )
        .all()
    )
    by_id = {folder.id: folder for folder in folders}
    if len(by_id) != len(folder_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder hierarchy is invalid",
        )
    return [
        {"id": folder_id, "name": by_id[folder_id].name}
        for folder_id in folder_ids
    ]


def _normalize_filter(
    value: str | None,
    *,
    field_name: str,
    maximum: int,
) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
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


def get_document_explorer(
    db: Session,
    project_id: int,
    *,
    folder_id: int | None,
    search: str | None,
    document_type: str | None,
    mime_type: str | None,
    extension: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
    extraction_config: DocumentExtractionConfig = DOCUMENT_EXTRACTION_CONFIG,
) -> dict:
    current_folder = (
        get_project_folder(db, project_id, folder_id)
        if folder_id is not None
        else None
    )
    child_counts, document_counts = _folder_count_maps(db, project_id)
    folder_query = db.query(Folder).filter(
        Folder.project_id == project_id,
        Folder.deleted_at.is_(None),
    )
    if current_folder is None:
        folder_query = folder_query.filter(
            Folder.parent_folder_id.is_(None)
        )
    else:
        folder_query = folder_query.filter(
            Folder.parent_folder_id == current_folder.id
        )
    folders = folder_query.order_by(
        func.lower(Folder.name).asc(),
        Folder.id.asc(),
    ).all()

    query = _active_document_query(db, project_id)
    if current_folder is None:
        query = query.filter(Document.folder_id.is_(None))
    else:
        query = query.filter(Document.folder_id == current_folder.id)

    normalized_search = _normalize_filter(
        search,
        field_name="search query",
        maximum=200,
    )
    if normalized_search:
        escaped = (
            normalized_search.lower()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        query = query.filter(
            or_(
                func.lower(Document.display_name).like(
                    pattern,
                    escape="\\",
                ),
                func.lower(Document.original_filename).like(
                    pattern,
                    escape="\\",
                ),
                func.lower(Document.extension).like(pattern, escape="\\"),
                func.lower(Document.document_type).like(
                    pattern,
                    escape="\\",
                ),
                func.lower(Document.mime_type).like(pattern, escape="\\"),
            )
        )

    normalized_document_type = _normalize_filter(
        document_type,
        field_name="document type",
        maximum=MAX_DOCUMENT_TYPE_LENGTH,
    )
    if normalized_document_type:
        query = query.filter(
            func.lower(Document.document_type)
            == normalized_document_type.lower()
        )

    normalized_mime_type = _normalize_filter(
        mime_type,
        field_name="MIME type",
        maximum=255,
    )
    if normalized_mime_type:
        query = query.filter(
            func.lower(Document.mime_type) == normalized_mime_type.lower()
        )

    normalized_extension = _normalize_filter(
        extension,
        field_name="file extension",
        maximum=MAX_EXTENSION_LENGTH,
    )
    if normalized_extension:
        extension_value = normalized_extension.lower()
        if not extension_value.startswith("."):
            extension_value = f".{extension_value}"
        query = query.filter(Document.extension == extension_value)

    total = query.count()
    sort_columns = {
        "name": func.lower(Document.display_name),
        "created_at": Document.created_at,
        "updated_at": Document.updated_at,
        "size_bytes": Document.size_bytes,
        "document_type": func.lower(Document.document_type),
    }
    primary_order = (
        sort_columns[sort].desc()
        if order == "desc"
        else sort_columns[sort].asc()
    )
    documents = (
        query.order_by(primary_order, Document.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    extraction_summaries = get_document_extraction_summaries(
        db,
        documents,
        extraction_config,
    )

    return {
        "project_id": project_id,
        "current_folder": (
            _folder_response(
                current_folder,
                child_counts,
                document_counts,
            )
            if current_folder
            else None
        ),
        "breadcrumbs": _folder_breadcrumbs(
            db,
            project_id,
            current_folder,
        ),
        "folders": [
            _folder_response(folder, child_counts, document_counts)
            for folder in folders
        ],
        "documents": [
            _document_response(
                document,
                extraction_summaries[document.id],
            )
            for document in documents
        ],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(documents) < total,
        },
    }


def get_folder_tree(db: Session, project_id: int) -> list[dict]:
    folders = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.deleted_at.is_(None),
        )
        .order_by(func.lower(Folder.name).asc(), Folder.id.asc())
        .limit(MAX_FOLDER_TREE_ITEMS + 1)
        .all()
    )
    if len(folders) > MAX_FOLDER_TREE_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder tree exceeds the supported size",
        )

    by_id = {folder.id: folder for folder in folders}
    for folder in folders:
        seen: set[int] = set()
        current = folder
        depth = 0
        while current.parent_folder_id is not None:
            if current.id in seen or depth >= MAX_FOLDER_DEPTH:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Folder hierarchy is invalid",
                )
            seen.add(current.id)
            current = by_id.get(current.parent_folder_id)
            if current is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Folder hierarchy is invalid",
                )
            depth += 1

    child_counts, document_counts = _folder_count_maps(db, project_id)
    return [
        _folder_response(folder, child_counts, document_counts)
        for folder in folders
    ]


def get_recent_documents(
    db: Session,
    project_id: int,
    *,
    limit: int,
    extraction_config: DocumentExtractionConfig = DOCUMENT_EXTRACTION_CONFIG,
) -> list[dict]:
    documents = (
        _active_document_query(db, project_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .all()
    )
    summaries = get_document_extraction_summaries(
        db,
        documents,
        extraction_config,
    )
    return [
        _document_response(document, summaries[document.id])
        for document in documents
    ]


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

    from app.models.drawing import DrawingRevision

    drawing_revision = (
        db.query(DrawingRevision.id)
        .filter(DrawingRevision.document_id == document.id)
        .first()
    )
    if drawing_revision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Drawing revision documents must be retained in drawing "
                "history"
            ),
        )

    document.deleted_at = utc_now()
    document.is_current_version = False
    document.status = "Deleted"
    cancel_document_extraction(db, document)
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
