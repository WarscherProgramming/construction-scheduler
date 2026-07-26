from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
import logging
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.attachment import Attachment
from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.project import Project
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.storage.attachment import (
    AttachmentObjectMissing,
    AttachmentStorage,
    AttachmentStorageError,
)


logger = logging.getLogger(__name__)

MAX_FILENAME_LENGTH = 255
MULTIPART_OVERHEAD_ALLOWANCE = 1_048_576


@dataclass(frozen=True)
class FileRule:
    mime_types: frozenset[str]
    signature: str
    inline: bool = False


# PDF and raster formats receive signature validation. Text receives UTF-8
# and NUL checks. Legacy and OOXML Office formats receive container-signature
# validation only; distinguishing content inside OLE/ZIP containers would
# require a heavier file-analysis dependency.
FILE_RULES = {
    ".pdf": FileRule(frozenset({"application/pdf"}), "pdf", True),
    ".jpg": FileRule(frozenset({"image/jpeg"}), "jpeg", True),
    ".jpeg": FileRule(frozenset({"image/jpeg"}), "jpeg", True),
    ".png": FileRule(frozenset({"image/png"}), "png", True),
    ".webp": FileRule(frozenset({"image/webp"}), "webp", True),
    ".heic": FileRule(
        frozenset({"image/heic", "image/heif"}),
        "heif",
        True,
    ),
    ".heif": FileRule(
        frozenset({"image/heic", "image/heif"}),
        "heif",
        True,
    ),
    ".txt": FileRule(frozenset({"text/plain"}), "text"),
    ".csv": FileRule(frozenset({"text/csv"}), "text"),
    ".doc": FileRule(frozenset({"application/msword"}), "ole"),
    ".xls": FileRule(
        frozenset({"application/vnd.ms-excel"}),
        "ole",
    ),
    ".docx": FileRule(
        frozenset(
            {
                (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            }
        ),
        "zip",
    ),
    ".xlsx": FileRule(
        frozenset(
            {
                (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            }
        ),
        "zip",
    ),
}

PARENT_MODELS = {
    "daily_log": DailyLog,
    "rfi": RFI,
    "submittal": Submittal,
    "punch_item": PunchItem,
    "change_order": ChangeOrder,
}


def normalize_parent_type(parent_type: str) -> str:
    normalized = str(parent_type or "").strip().lower()
    if normalized != "project" and normalized not in PARENT_MODELS:
        allowed = ", ".join(["project", *PARENT_MODELS])
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"parent_type must be one of: {allowed}",
        )
    return normalized


def resolve_attachment_parent(
    db: Session,
    project_id: int,
    parent_type: str,
    parent_id: int,
) -> str:
    normalized_type = normalize_parent_type(parent_type)

    if normalized_type == "project":
        parent_exists = parent_id == project_id
    else:
        model = PARENT_MODELS[normalized_type]
        parent_exists = (
            db.query(model)
            .filter(
                model.id == parent_id,
                model.project_id == project_id,
            )
            .first()
            is not None
        )

    if not parent_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment parent not found",
        )

    return normalized_type


def sanitize_attachment_filename(filename: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(filename or ""))
    normalized = normalized.replace("\\", "/").split("/")[-1]
    normalized = "".join(
        character
        for character in normalized
        if character != "\x00"
        and not unicodedata.category(character).startswith("C")
    )
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")

    if not normalized or normalized in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid filename is required",
        )

    extension = Path(normalized).suffix.lower()
    if extension not in FILE_RULES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported attachment file extension",
        )

    stem = normalized[: -len(extension)].rstrip(" .")
    if not stem:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid filename is required",
        )

    stem = stem[: MAX_FILENAME_LENGTH - len(extension)].rstrip(" .")
    if not stem:
        stem = "attachment"

    return f"{stem}{extension}"


def validated_file_rule(
    filename: str,
    declared_mime_type: str | None,
    config: AttachmentConfig,
) -> tuple[str, FileRule]:
    extension = Path(filename).suffix.lower()
    rule = FILE_RULES[extension]
    mime_type = str(declared_mime_type or "").split(";", 1)[0].strip().lower()

    if (
        mime_type not in rule.mime_types
        or mime_type not in config.permitted_mime_types
    ):
        logger.info(
            "Rejected attachment with mismatched type for extension %s",
            extension,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Attachment extension and content type do not match",
        )

    return mime_type, rule


def validate_file_signature(sample: bytes, rule: FileRule) -> None:
    valid = False

    if rule.signature == "pdf":
        valid = sample.startswith(b"%PDF-")
    elif rule.signature == "jpeg":
        valid = sample.startswith(b"\xff\xd8\xff")
    elif rule.signature == "png":
        valid = sample.startswith(b"\x89PNG\r\n\x1a\n")
    elif rule.signature == "webp":
        valid = (
            len(sample) >= 12
            and sample.startswith(b"RIFF")
            and sample[8:12] == b"WEBP"
        )
    elif rule.signature == "heif":
        brands = {
            b"heic",
            b"heix",
            b"hevc",
            b"hevx",
            b"heim",
            b"heis",
            b"mif1",
            b"msf1",
        }
        valid = (
            len(sample) >= 12
            and sample[4:8] == b"ftyp"
            and any(
                sample[offset : offset + 4] in brands
                for offset in range(8, min(len(sample), 64), 4)
            )
        )
    elif rule.signature == "ole":
        valid = sample.startswith(
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        )
    elif rule.signature == "zip":
        valid = sample.startswith(
            (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        )
    elif rule.signature == "text":
        try:
            sample.decode("utf-8-sig")
            valid = b"\x00" not in sample
        except UnicodeDecodeError:
            valid = False

    if not valid:
        logger.info(
            "Rejected attachment after %s signature validation",
            rule.signature,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Attachment content does not match its file type",
        )


def list_attachment_records(
    db: Session,
    project_id: int,
    parent_type: str,
    parent_id: int,
) -> list[Attachment]:
    normalized_type = resolve_attachment_parent(
        db,
        project_id,
        parent_type,
        parent_id,
    )
    return (
        db.query(Attachment)
        .filter(
            Attachment.project_id == project_id,
            Attachment.parent_type == normalized_type,
            Attachment.parent_id == parent_id,
        )
        .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        .all()
    )


def create_attachment(
    db: Session,
    storage: AttachmentStorage,
    config: AttachmentConfig,
    *,
    project_id: int,
    parent_type: str,
    parent_id: int,
    upload: UploadFile,
    uploaded_by: int,
    content_length: int | None,
) -> Attachment:
    normalized_type = resolve_attachment_parent(
        db,
        project_id,
        parent_type,
        parent_id,
    )
    filename = sanitize_attachment_filename(upload.filename)
    mime_type, rule = validated_file_rule(
        filename,
        upload.content_type,
        config,
    )

    if (
        content_length is not None
        and content_length
        > config.max_upload_size + MULTIPART_OVERHEAD_ALLOWANCE
    ):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Attachment exceeds the maximum upload size",
        )

    if upload.size is not None and upload.size > config.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Attachment exceeds the maximum upload size",
        )

    upload.file.seek(0)
    first_chunk = upload.file.read(max(config.upload_chunk_size, 512))
    if not first_chunk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Empty attachments are not allowed",
        )
    validate_file_signature(first_chunk, rule)

    digest = sha256()
    size_bytes = 0

    def upload_chunks() -> Iterator[bytes]:
        nonlocal size_bytes
        chunk = first_chunk

        while chunk:
            size_bytes += len(chunk)
            if size_bytes > config.max_upload_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Attachment exceeds the maximum upload size",
                )
            digest.update(chunk)
            yield chunk
            chunk = upload.file.read(config.upload_chunk_size)

    storage_key = uuid.uuid4().hex
    try:
        storage.put_stream(storage_key, upload_chunks())
    except HTTPException:
        raise
    except AttachmentStorageError as error:
        logger.exception(
            "Attachment upload failed for provider %s",
            storage.provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error

    attachment = Attachment(
        project_id=project_id,
        parent_type=normalized_type,
        parent_id=parent_id,
        original_filename=filename,
        storage_key=storage_key,
        storage_provider=storage.provider_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
        sha256=digest.hexdigest(),
    )
    db.add(attachment)

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        try:
            storage.delete(storage_key)
        except AttachmentStorageError:
            logger.exception(
                "Attachment metadata failed and storage cleanup also failed "
                "for key %s",
                storage_key,
            )
        else:
            logger.exception(
                "Attachment metadata persistence failed; stored object was "
                "removed"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save attachment metadata",
        ) from error

    db.refresh(attachment)
    return attachment


def get_project_attachment(
    db: Session,
    project_id: int,
    attachment_id: int,
) -> Attachment:
    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.project_id == project_id,
        )
        .first()
    )
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    resolve_attachment_parent(
        db,
        project_id,
        attachment.parent_type,
        attachment.parent_id,
    )
    return attachment


def open_attachment_stream(
    storage: AttachmentStorage,
    attachment: Attachment,
    chunk_size: int,
) -> Iterator[bytes]:
    try:
        return storage.open_stream(attachment.storage_key, chunk_size)
    except AttachmentObjectMissing as error:
        logger.error(
            "Stored content is missing for attachment %s",
            attachment.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment content is unavailable",
        ) from error
    except AttachmentStorageError as error:
        logger.exception(
            "Attachment provider failed while opening attachment %s",
            attachment.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error


def content_disposition(attachment: Attachment) -> str:
    rule = FILE_RULES[Path(attachment.original_filename).suffix.lower()]
    disposition = "inline" if rule.inline else "attachment"
    fallback = "".join(
        character
        if 32 <= ord(character) < 127
        and character not in {'"', "\\", ";"}
        else "_"
        for character in attachment.original_filename
    )
    encoded = quote(attachment.original_filename, safe="")
    return (
        f'{disposition}; filename="{fallback}"; '
        f"filename*=UTF-8''{encoded}"
    )


def delete_attachment(
    db: Session,
    storage: AttachmentStorage,
    attachment: Attachment,
) -> None:
    try:
        existed = storage.delete(attachment.storage_key)
    except AttachmentStorageError as error:
        logger.exception(
            "Attachment provider failed while deleting attachment %s",
            attachment.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error

    if not existed:
        logger.warning(
            "Stored content was already missing for attachment %s",
            attachment.id,
        )

    db.delete(attachment)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception(
            "Attachment metadata deletion failed after object removal for %s",
            attachment.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete attachment metadata",
        ) from error


def delete_attachments_for_parent(
    db: Session,
    storage: AttachmentStorage,
    project_id: int,
    parent_type: str,
    parent_id: int,
    *,
    commit: bool = True,
) -> int:
    attachments = list_attachment_records(
        db,
        project_id,
        parent_type,
        parent_id,
    )

    try:
        for attachment in attachments:
            storage.delete(attachment.storage_key)
    except AttachmentStorageError as error:
        logger.exception(
            "Attachment cleanup failed for parent type %s and ID %s",
            parent_type,
            parent_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from error

    for attachment in attachments:
        db.delete(attachment)

    if commit:
        db.commit()

    return len(attachments)
