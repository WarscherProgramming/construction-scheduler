from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig, DocumentExtractionConfig
from app.extraction import (
    DisabledOCRProvider,
    EXTRACTOR_VERSION,
    ExtractionError,
    OCRProvider,
    extract_document_content,
)
from app.extraction.pdf import SUPPORTED_EXTRACTION_MIME_TYPES
from app.models.document import Document
from app.models.document_extraction import (
    DocumentExtraction,
    DocumentExtractionJob,
    DocumentPageText,
)
from app.storage.provider import StorageProvider, StorageProviderError


logger = logging.getLogger(__name__)
ACTIVE_JOB_STATUSES = ("pending", "processing")
TERMINAL_JOB_STATUSES = ("completed", "failed", "cancelled")
SAFE_FAILURE_MESSAGES = {
    "checksum_mismatch": "Stored document content no longer matches its metadata",
    "corrupt_file": "The document could not be read",
    "encrypted_pdf": "Encrypted PDFs are not supported",
    "extraction_disabled": "Document text extraction is disabled",
    "image_limit_exceeded": "Document image exceeds processing limits",
    "not_processed": "Document text has not been processed",
    "ocr_failed": "OCR could not process the document",
    "ocr_timeout": "OCR processing timed out",
    "ocr_unavailable": "OCR is not available for this document",
    "page_limit_exceeded": "Document exceeds the processing page limit",
    "parser_timeout": "Document extraction timed out",
    "storage_unavailable": "Document content is temporarily unavailable",
    "temporary_failure": "Document extraction is temporarily unavailable",
    "text_limit_exceeded": "Extracted text was truncated at configured limits",
    "unsupported_type": "This document type supports metadata search only",
}
StorageResolver = Callable[[str], StorageProvider]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ClaimedExtractionJob:
    job_id: int
    lease_token: str


@dataclass
class ExtractionProcessingResult:
    claimed: int = 0
    completed: int = 0
    unavailable: int = 0
    retryable: int = 0
    failed: int = 0
    cancelled: int = 0
    skipped: int = 0


def build_ocr_provider(config: DocumentExtractionConfig) -> OCRProvider:
    if config.ocr_provider == "disabled":
        return DisabledOCRProvider()
    raise RuntimeError("Unsupported OCR provider")


def is_supported_document(document: Document) -> bool:
    return document.mime_type in SUPPORTED_EXTRACTION_MIME_TYPES


def _safe_message(code: str) -> str:
    return SAFE_FAILURE_MESSAGES.get(
        code,
        "Document extraction could not be completed",
    )


def _get_or_create_extraction(
    db: Session,
    document: Document,
    config: DocumentExtractionConfig,
) -> DocumentExtraction:
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == document.id)
        .first()
    )
    if extraction is None:
        extraction = DocumentExtraction(
            project_id=document.project_id,
            document_id=document.id,
            status="pending",
            extraction_method="unavailable",
            page_count=0,
            pages_processed=0,
            text_character_count=0,
            searchable=False,
            language=config.ocr_language,
            extractor_version=EXTRACTOR_VERSION,
            source_checksum=document.checksum_sha256,
        )
        db.add(extraction)
        db.flush()
    return extraction


def _mark_unavailable(
    extraction: DocumentExtraction,
    *,
    code: str,
    method: str,
) -> None:
    now = utc_now()
    extraction.status = "unavailable"
    extraction.extraction_method = method
    extraction.page_count = 0
    extraction.pages_processed = 0
    extraction.text_character_count = 0
    extraction.searchable = False
    extraction.completed_at = now
    extraction.failed_at = None
    extraction.failure_code = code
    extraction.failure_message = _safe_message(code)
    extraction.warning_codes = code
    extraction.updated_at = now


def enqueue_document_extraction(
    db: Session,
    document: Document,
    requested_by: int,
    config: DocumentExtractionConfig,
    *,
    force: bool = False,
) -> tuple[DocumentExtraction, DocumentExtractionJob | None]:
    extraction = _get_or_create_extraction(db, document, config)
    if not extraction.searchable:
        extraction.language = config.ocr_language
        extraction.extractor_version = EXTRACTOR_VERSION

    if document.deleted_at is not None:
        extraction.status = "cancelled"
        extraction.failure_code = None
        extraction.failure_message = None
        extraction.updated_at = utc_now()
        return extraction, None
    if not config.enabled:
        _mark_unavailable(
            extraction,
            code="extraction_disabled",
            method="unavailable",
        )
        return extraction, None
    if not is_supported_document(document):
        _mark_unavailable(
            extraction,
            code="unsupported_type",
            method="metadata_only",
        )
        return extraction, None
    if (
        not force
        and extraction.source_checksum == document.checksum_sha256
        and extraction.extractor_version == EXTRACTOR_VERSION
        and extraction.status in {"completed", "completed_with_warnings"}
    ):
        return extraction, None

    active = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.document_id == document.id,
            DocumentExtractionJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(DocumentExtractionJob.created_at.desc())
        .first()
    )
    if active is not None:
        return extraction, active

    now = utc_now()
    job = DocumentExtractionJob(
        project_id=document.project_id,
        document_id=document.id,
        requested_by=requested_by,
        status="pending",
        attempt_count=0,
        available_at=now,
        source_checksum=document.checksum_sha256,
        extractor_version=EXTRACTOR_VERSION,
    )
    db.add(job)
    extraction.status = "pending"
    if not extraction.searchable:
        extraction.source_checksum = document.checksum_sha256
    extraction.failure_code = None
    extraction.failure_message = None
    extraction.failed_at = None
    extraction.updated_at = now
    try:
        db.flush()
    except IntegrityError:
        raise
    logger.info(
        "Queued document extraction job for document %s in project %s",
        document.id,
        document.project_id,
    )
    return extraction, job


def cancel_document_extraction(db: Session, document: Document) -> None:
    now = utc_now()
    (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.document_id == document.id,
            DocumentExtractionJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .update(
            {
                DocumentExtractionJob.status: "cancelled",
                DocumentExtractionJob.completed_at: now,
                DocumentExtractionJob.lease_expires_at: None,
                DocumentExtractionJob.lease_token: None,
                DocumentExtractionJob.updated_at: now,
            },
            synchronize_session=False,
        )
    )
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == document.id)
        .first()
    )
    if extraction is not None:
        extraction.status = "cancelled"
        extraction.updated_at = now


def extraction_summary(
    extraction: DocumentExtraction | None,
    document: Document,
    config: DocumentExtractionConfig,
    *,
    active_job: DocumentExtractionJob | None = None,
) -> dict:
    supported = is_supported_document(document)
    if extraction is None:
        if supported:
            code = (
                "not_processed" if config.enabled else "extraction_disabled"
            )
        else:
            code = "unsupported_type"
        return {
            "status": "unavailable",
            "extraction_method": (
                "unavailable" if supported else "metadata_only"
            ),
            "page_count": 0,
            "pages_processed": 0,
            "text_character_count": 0,
            "searchable": False,
            "language": config.ocr_language,
            "warning_codes": [code],
            "started_at": None,
            "completed_at": None,
            "failed_at": None,
            "failure_code": code,
            "failure_message": _safe_message(code),
            "extractor_version": EXTRACTOR_VERSION,
            "source_current": False,
            "job_status": None,
            "retry_eligible": supported and config.enabled,
        }

    warning_codes = [
        code
        for code in (extraction.warning_codes or "").split(",")
        if code
    ]
    source_current = extraction.source_checksum == document.checksum_sha256
    return {
        "status": extraction.status,
        "extraction_method": extraction.extraction_method,
        "page_count": extraction.page_count,
        "pages_processed": extraction.pages_processed,
        "text_character_count": extraction.text_character_count,
        "searchable": extraction.searchable and source_current,
        "language": extraction.language,
        "warning_codes": warning_codes,
        "started_at": extraction.started_at,
        "completed_at": extraction.completed_at,
        "failed_at": extraction.failed_at,
        "failure_code": extraction.failure_code,
        "failure_message": extraction.failure_message,
        "extractor_version": extraction.extractor_version,
        "source_current": source_current,
        "job_status": active_job.status if active_job is not None else None,
        "retry_eligible": (
            supported
            and config.enabled
            and active_job is None
            and extraction.status != "processing"
        ),
    }


def get_document_extraction_summary(
    db: Session,
    document: Document,
    config: DocumentExtractionConfig,
) -> dict:
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == document.id)
        .first()
    )
    active_job = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.document_id == document.id,
            DocumentExtractionJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(DocumentExtractionJob.created_at.desc())
        .first()
    )
    return extraction_summary(
        extraction,
        document,
        config,
        active_job=active_job,
    )


def get_document_extraction_summaries(
    db: Session,
    documents: Iterable[Document],
    config: DocumentExtractionConfig,
) -> dict[int, dict]:
    document_list = list(documents)
    if not document_list:
        return {}
    document_ids = [document.id for document in document_list]
    extractions = {
        extraction.document_id: extraction
        for extraction in (
            db.query(DocumentExtraction)
            .filter(DocumentExtraction.document_id.in_(document_ids))
            .all()
        )
    }
    active_jobs = {}
    for job in (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.document_id.in_(document_ids),
            DocumentExtractionJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(
            DocumentExtractionJob.document_id.asc(),
            DocumentExtractionJob.created_at.desc(),
        )
        .all()
    ):
        active_jobs.setdefault(job.document_id, job)
    return {
        document.id: extraction_summary(
            extractions.get(document.id),
            document,
            config,
            active_job=active_jobs.get(document.id),
        )
        for document in document_list
    }


def claim_extraction_jobs(
    db: Session,
    *,
    batch_size: int,
    lease_seconds: int,
    max_attempts: int,
    document_id: int | None = None,
    now: datetime | None = None,
) -> tuple[ClaimedExtractionJob, ...]:
    current_time = now or utc_now()
    expired_jobs = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.status == "processing",
            DocumentExtractionJob.lease_expires_at <= current_time,
        )
        .order_by(
            DocumentExtractionJob.lease_expires_at.asc(),
            DocumentExtractionJob.id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    for expired_job in expired_jobs:
        expired_job.lease_expires_at = None
        expired_job.lease_token = None
        expired_job.updated_at = current_time
        extraction = (
            db.query(DocumentExtraction)
            .filter(
                DocumentExtraction.document_id == expired_job.document_id
            )
            .first()
        )
        if expired_job.attempt_count >= max_attempts:
            expired_job.status = "failed"
            expired_job.completed_at = current_time
            expired_job.last_error_code = "temporary_failure"
            expired_job.last_error_message = _safe_message(
                "temporary_failure"
            )
            if extraction is not None:
                extraction.status = "failed"
                extraction.failure_code = "temporary_failure"
                extraction.failure_message = _safe_message(
                    "temporary_failure"
                )
                extraction.failed_at = current_time
                extraction.updated_at = current_time
        else:
            expired_job.status = "pending"
            expired_job.available_at = current_time
            if extraction is not None:
                extraction.status = "pending"
                extraction.updated_at = current_time
    db.flush()
    query = db.query(DocumentExtractionJob).filter(
        DocumentExtractionJob.status == "pending",
        DocumentExtractionJob.available_at <= current_time,
    )
    if document_id is not None:
        query = query.filter(DocumentExtractionJob.document_id == document_id)
    jobs = (
        query.order_by(
            DocumentExtractionJob.available_at.asc(),
            DocumentExtractionJob.created_at.asc(),
            DocumentExtractionJob.id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    claims: list[ClaimedExtractionJob] = []
    for job in jobs:
        token = uuid.uuid4().hex
        job.status = "processing"
        job.attempt_count += 1
        job.started_at = current_time
        job.lease_expires_at = current_time + timedelta(seconds=lease_seconds)
        job.lease_token = token
        job.updated_at = current_time
        extraction = (
            db.query(DocumentExtraction)
            .filter(DocumentExtraction.document_id == job.document_id)
            .first()
        )
        if extraction is not None:
            extraction.status = "processing"
            extraction.started_at = current_time
            extraction.updated_at = current_time
        claims.append(ClaimedExtractionJob(job.id, token))
    db.commit()
    return tuple(claims)


def _read_document_content(
    storage: StorageProvider,
    document: Document,
    storage_config: AttachmentConfig,
) -> bytes:
    maximum = min(storage_config.max_upload_size, document.size_bytes)
    digest = sha256()
    content = bytearray()
    try:
        chunks = storage.open_stream(
            document.storage_key,
            storage_config.upload_chunk_size,
        )
        for chunk in chunks:
            if not chunk:
                continue
            if len(content) + len(chunk) > maximum:
                raise ExtractionError(
                    "checksum_mismatch",
                    _safe_message("checksum_mismatch"),
                )
            content.extend(chunk)
            digest.update(chunk)
    except StorageProviderError as error:
        raise ExtractionError(
            "storage_unavailable",
            _safe_message("storage_unavailable"),
            retryable=error.retryable,
        ) from error
    if (
        len(content) != document.size_bytes
        or digest.hexdigest() != document.checksum_sha256
    ):
        raise ExtractionError(
            "checksum_mismatch",
            _safe_message("checksum_mismatch"),
        )
    return bytes(content)


def _retry_delay(
    config: DocumentExtractionConfig,
    attempt_count: int,
) -> int:
    delay = config.retry_base_seconds * (2 ** max(attempt_count - 1, 0))
    return min(delay, config.retry_max_seconds)


def _record_job_failure(
    db: Session,
    claim: ClaimedExtractionJob,
    error: ExtractionError,
    config: DocumentExtractionConfig,
) -> str:
    job = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.id == claim.job_id,
            DocumentExtractionJob.status == "processing",
            DocumentExtractionJob.lease_token == claim.lease_token,
        )
        .with_for_update()
        .first()
    )
    if job is None:
        db.rollback()
        return "skipped"
    now = utc_now()
    retryable = error.retryable and job.attempt_count < config.max_attempts
    job.status = "pending" if retryable else "failed"
    job.available_at = now + timedelta(
        seconds=_retry_delay(config, job.attempt_count)
    )
    job.last_error_code = error.code[:50]
    job.last_error_message = _safe_message(error.code)[:300]
    job.completed_at = None if retryable else now
    job.lease_expires_at = None
    job.lease_token = None
    job.updated_at = now
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == job.document_id)
        .first()
    )
    if extraction is not None:
        extraction.status = "pending" if retryable else "failed"
        extraction.failure_code = error.code[:50]
        extraction.failure_message = _safe_message(error.code)[:300]
        extraction.failed_at = None if retryable else now
        extraction.updated_at = now
    db.commit()
    logger.warning(
        "Document extraction job %s ended with failure category %s",
        job.id,
        error.code,
    )
    return "retryable" if retryable else "failed"


def _cancel_claim(
    db: Session,
    claim: ClaimedExtractionJob,
) -> str:
    job = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.id == claim.job_id,
            DocumentExtractionJob.status == "processing",
            DocumentExtractionJob.lease_token == claim.lease_token,
        )
        .first()
    )
    if job is None:
        db.rollback()
        return "skipped"
    now = utc_now()
    job.status = "cancelled"
    job.completed_at = now
    job.lease_expires_at = None
    job.lease_token = None
    job.updated_at = now
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == job.document_id)
        .first()
    )
    if extraction is not None:
        extraction.status = "cancelled"
        extraction.updated_at = now
    db.commit()
    return "cancelled"


def _complete_claim(
    db: Session,
    claim: ClaimedExtractionJob,
    result,
    config: DocumentExtractionConfig,
) -> str:
    job = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.id == claim.job_id,
            DocumentExtractionJob.status == "processing",
            DocumentExtractionJob.lease_token == claim.lease_token,
        )
        .with_for_update()
        .first()
    )
    if job is None:
        db.rollback()
        return "skipped"
    document = db.get(Document, job.document_id)
    extraction = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == job.document_id)
        .with_for_update()
        .one()
    )
    if (
        document is None
        or document.deleted_at is not None
        or document.checksum_sha256 != job.source_checksum
    ):
        return _cancel_claim(db, claim)

    now = utc_now()
    keep_previous = result.status == "unavailable" and extraction.searchable
    if not keep_previous:
        (
            db.query(DocumentPageText)
            .filter(DocumentPageText.extraction_id == extraction.id)
            .delete(synchronize_session=False)
        )
        dialect = db.get_bind().dialect.name
        for page in result.pages:
            normalized = page.text.casefold()
            page_row = DocumentPageText(
                project_id=document.project_id,
                extraction_id=extraction.id,
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                normalized_text=normalized,
                extraction_method=page.extraction_method,
                confidence=page.confidence,
                character_count=len(page.text),
            )
            page_row.search_vector = (
                func.to_tsvector("simple", normalized)
                if dialect == "postgresql"
                else normalized
            )
            db.add(page_row)
        extraction.status = result.status
        extraction.extraction_method = result.extraction_method
        extraction.page_count = result.page_count
        extraction.pages_processed = result.pages_processed
        extraction.text_character_count = result.character_count
        extraction.searchable = result.searchable
    else:
        extraction.status = "completed_with_warnings"
    extraction.source_checksum = document.checksum_sha256
    extraction.extractor_version = EXTRACTOR_VERSION
    extraction.language = config.ocr_language
    extraction.completed_at = now
    extraction.failed_at = None
    extraction.failure_code = (
        result.warning_codes[0] if result.warning_codes else None
    )
    extraction.failure_message = (
        _safe_message(result.warning_codes[0])
        if result.warning_codes
        else None
    )
    extraction.warning_codes = ",".join(result.warning_codes) or None
    extraction.updated_at = now
    job.status = "completed"
    job.completed_at = now
    job.last_error_code = None
    job.last_error_message = None
    job.lease_expires_at = None
    job.lease_token = None
    job.updated_at = now
    db.commit()
    return "unavailable" if result.status == "unavailable" else "completed"


def process_extraction_claim(
    db: Session,
    claim: ClaimedExtractionJob,
    storage_resolver: StorageResolver,
    storage_config: AttachmentConfig,
    extraction_config: DocumentExtractionConfig,
    ocr_provider: OCRProvider,
) -> str:
    job = db.get(DocumentExtractionJob, claim.job_id)
    if (
        job is None
        or job.status != "processing"
        or job.lease_token != claim.lease_token
    ):
        return "skipped"
    document = db.get(Document, job.document_id)
    if document is None or document.deleted_at is not None:
        return _cancel_claim(db, claim)
    if document.checksum_sha256 != job.source_checksum:
        return _record_job_failure(
            db,
            claim,
            ExtractionError(
                "checksum_mismatch",
                _safe_message("checksum_mismatch"),
            ),
            extraction_config,
        )
    try:
        storage = storage_resolver(document.storage_provider)
        content = _read_document_content(storage, document, storage_config)
        result = extract_document_content(
            content,
            document.mime_type,
            ocr_provider,
            extraction_config,
        )
    except ExtractionError as error:
        return _record_job_failure(
            db,
            claim,
            error,
            extraction_config,
        )
    except Exception:
        logger.error(
            "Document extraction ended with an unexpected safe failure "
            "for document %s",
            document.id,
        )
        return _record_job_failure(
            db,
            claim,
            ExtractionError(
                "temporary_failure",
                _safe_message("temporary_failure"),
                retryable=True,
            ),
            extraction_config,
        )
    return _complete_claim(db, claim, result, extraction_config)


def process_extraction_jobs(
    db: Session,
    storage_resolver: StorageResolver,
    storage_config: AttachmentConfig,
    extraction_config: DocumentExtractionConfig,
    *,
    ocr_provider: OCRProvider | None = None,
    batch_size: int | None = None,
    max_jobs: int | None = None,
    document_id: int | None = None,
    lease_seconds: int | None = None,
) -> ExtractionProcessingResult:
    if not extraction_config.enabled:
        return ExtractionProcessingResult()
    configured_batch = batch_size or extraction_config.batch_size
    remaining = max_jobs or configured_batch
    provider = ocr_provider or build_ocr_provider(extraction_config)
    result = ExtractionProcessingResult()
    while remaining > 0:
        claims = claim_extraction_jobs(
            db,
            batch_size=min(configured_batch, remaining),
            lease_seconds=lease_seconds or extraction_config.lease_seconds,
            max_attempts=extraction_config.max_attempts,
            document_id=document_id,
        )
        if not claims:
            break
        result.claimed += len(claims)
        remaining -= len(claims)
        for claim in claims:
            outcome = process_extraction_claim(
                db,
                claim,
                storage_resolver,
                storage_config,
                extraction_config,
                provider,
            )
            if hasattr(result, outcome):
                setattr(result, outcome, getattr(result, outcome) + 1)
            else:
                result.skipped += 1
    return result


def retry_failed_extractions(
    db: Session,
    config: DocumentExtractionConfig,
    *,
    requested_by: int,
    document_id: int | None = None,
    limit: int,
) -> int:
    query = (
        db.query(Document)
        .join(
            DocumentExtraction,
            DocumentExtraction.document_id == Document.id,
        )
        .filter(
            Document.deleted_at.is_(None),
            DocumentExtraction.status == "failed",
        )
    )
    if document_id is not None:
        query = query.filter(Document.id == document_id)
    documents = query.order_by(Document.id.asc()).limit(limit).all()
    queued = 0
    for document in documents:
        _, job = enqueue_document_extraction(
            db,
            document,
            requested_by,
            config,
            force=True,
        )
        if job is not None:
            queued += 1
    db.commit()
    return queued


def prune_extraction_jobs(
    db: Session,
    config: DocumentExtractionConfig,
    *,
    now: datetime | None = None,
) -> int:
    cutoff = (now or utc_now()) - timedelta(days=config.retention_days)
    count = (
        db.query(DocumentExtractionJob)
        .filter(
            DocumentExtractionJob.status.in_(TERMINAL_JOB_STATUSES),
            DocumentExtractionJob.completed_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return count


def reprocess_document_extraction(
    db: Session,
    document: Document,
    user_id: int,
    config: DocumentExtractionConfig,
) -> dict:
    if document.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document extraction is disabled",
        )
    if not is_supported_document(document):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document type does not support content extraction",
        )
    try:
        extraction, job = enqueue_document_extraction(
            db,
            document,
            user_id,
            config,
            force=True,
        )
        db.commit()
        db.refresh(extraction)
        if job is not None:
            db.refresh(job)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document extraction is already queued",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to queue document extraction",
        ) from error
    return extraction_summary(
        extraction,
        document,
        config,
        active_job=job,
    )
