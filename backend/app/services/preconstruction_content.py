from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import unicodedata
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import PreconstructionPreparationConfig
from app.extraction.pdf import SUPPORTED_EXTRACTION_MIME_TYPES
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction, DocumentPageText
from app.models.drawing import DrawingRevision, DrawingSheet
from app.models.preconstruction import (
    PreconstructionContentPage,
    PreconstructionContentSegment,
    PreconstructionContentSnapshot,
    PreconstructionPreparationRun,
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)


SEARCHABLE_EXTRACTION_STATUSES = ("completed", "completed_with_warnings")
ACTIVE_PREPARATION_STATUSES = ("pending", "processing")
COMPLETED_SNAPSHOT_STATUSES = ("completed", "completed_with_warnings")
SAFE_PREPARATION_MESSAGES = {
    "document_unavailable": "The source document is no longer available",
    "source_checksum_changed": "The source no longer matches its pinned checksum",
    "drawing_revision_mismatch": "The drawing revision no longer matches its source document",
    "unsupported_type": "This source type cannot be prepared",
    "extraction_incomplete": "Source extraction is not complete",
    "extraction_unavailable": "Source extraction is unavailable",
    "extraction_checksum_changed": "Source extraction does not match the current document",
    "no_searchable_text": "No searchable text is available and production OCR is disabled",
    "page_limit_exceeded": "Source page count exceeds the preparation limit",
    "text_limit_exceeded": "Source text exceeds the preparation limit",
    "segment_limit_exceeded": "Source content exceeds the segment limit",
    "source_lineage_changed": "Source extraction changed before preparation completed",
    "lease_expired": "Source preparation lease expired",
    "preparation_failed": "Source content could not be prepared",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _safe_message(code: str) -> str:
    return SAFE_PREPARATION_MESSAGES.get(code, SAFE_PREPARATION_MESSAGES["preparation_failed"])


def _canonical_hash(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("utf-8")).hexdigest()


def _aware_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def build_lineage_payload(
    source: PreconstructionReviewSource,
    document: Document,
    extraction: DocumentExtraction,
    config: PreconstructionPreparationConfig,
) -> dict:
    return {
        "document_checksum": document.checksum_sha256,
        "drawing_revision_id": source.drawing_revision_id,
        "extraction_method": extraction.extraction_method,
        "extractor_version": extraction.extractor_version,
        "extraction_completed_at": _aware_iso(extraction.completed_at),
        "preparation_version": config.preparation_version,
        "renderer_version": None,
        "segmentation_policy_version": config.segmentation_policy_version,
    }


def lineage_fingerprint(
    source: PreconstructionReviewSource,
    document: Document,
    extraction: DocumentExtraction,
    config: PreconstructionPreparationConfig,
) -> str:
    return _canonical_hash(build_lineage_payload(source, document, extraction, config))


@dataclass(frozen=True)
class PreparationEligibility:
    eligible: bool
    code: str | None
    message: str | None
    document: Document | None
    extraction: DocumentExtraction | None
    fingerprint: str | None
    warning_codes: tuple[str, ...]


def get_preparation_source(
    db: Session,
    project_id: int,
    review_set_id: int,
    source_id: int,
    *,
    include_removed: bool = False,
) -> PreconstructionReviewSource:
    query = db.query(PreconstructionReviewSource).filter(
        PreconstructionReviewSource.id == source_id,
        PreconstructionReviewSource.project_id == project_id,
        PreconstructionReviewSource.review_set_id == review_set_id,
    )
    if not include_removed:
        query = query.filter(PreconstructionReviewSource.removed_at.is_(None))
    source = query.first()
    if source is None:
        raise _not_found("Preconstruction review source not found")
    return source


def evaluate_preparation_eligibility(
    db: Session,
    source: PreconstructionReviewSource,
    config: PreconstructionPreparationConfig,
) -> PreparationEligibility:
    document = db.query(Document).filter(
        Document.id == source.document_id,
        Document.project_id == source.project_id,
    ).first()
    if source.removed_at is not None or document is None or document.deleted_at is not None:
        return PreparationEligibility(False, "document_unavailable", _safe_message("document_unavailable"), document, None, None, ())
    if document.checksum_sha256 != source.source_checksum:
        return PreparationEligibility(False, "source_checksum_changed", _safe_message("source_checksum_changed"), document, None, None, ())
    if source.source_type == "drawing_revision":
        revision = db.query(DrawingRevision).filter(
            DrawingRevision.id == source.drawing_revision_id,
            DrawingRevision.project_id == source.project_id,
            DrawingRevision.document_id == document.id,
        ).first()
        if revision is None:
            return PreparationEligibility(False, "drawing_revision_mismatch", _safe_message("drawing_revision_mismatch"), document, None, None, ())
    if document.mime_type not in SUPPORTED_EXTRACTION_MIME_TYPES:
        return PreparationEligibility(False, "unsupported_type", _safe_message("unsupported_type"), document, None, None, ())
    extraction = db.query(DocumentExtraction).filter(
        DocumentExtraction.project_id == source.project_id,
        DocumentExtraction.document_id == document.id,
    ).first()
    if extraction is None or extraction.status not in SEARCHABLE_EXTRACTION_STATUSES:
        code = "extraction_unavailable" if extraction and extraction.status in ("failed", "unavailable", "cancelled") else "extraction_incomplete"
        return PreparationEligibility(False, code, _safe_message(code), document, extraction, None, ())
    if extraction.source_checksum != document.checksum_sha256:
        return PreparationEligibility(False, "extraction_checksum_changed", _safe_message("extraction_checksum_changed"), document, extraction, None, ())
    fingerprint = lineage_fingerprint(source, document, extraction, config)
    if extraction.page_count > config.max_pages:
        return PreparationEligibility(False, "page_limit_exceeded", _safe_message("page_limit_exceeded"), document, extraction, fingerprint, ())
    if extraction.text_character_count > config.max_total_characters:
        return PreparationEligibility(False, "text_limit_exceeded", _safe_message("text_limit_exceeded"), document, extraction, fingerprint, ())
    text_characters = db.query(func.coalesce(func.sum(DocumentPageText.character_count), 0)).filter(
        DocumentPageText.project_id == source.project_id,
        DocumentPageText.extraction_id == extraction.id,
    ).scalar()
    if not extraction.searchable or not text_characters:
        return PreparationEligibility(False, "no_searchable_text", _safe_message("no_searchable_text"), document, extraction, fingerprint, ())
    warnings = tuple(sorted(filter(None, (extraction.warning_codes or "").split(","))))
    return PreparationEligibility(True, None, None, document, extraction, fingerprint, warnings)


def _latest_snapshot_query(db: Session, project_id: int, source_id: int):
    return db.query(PreconstructionContentSnapshot).filter(
        PreconstructionContentSnapshot.project_id == project_id,
        PreconstructionContentSnapshot.review_source_id == source_id,
        PreconstructionContentSnapshot.status.in_(COMPLETED_SNAPSHOT_STATUSES),
    ).order_by(PreconstructionContentSnapshot.created_at.desc(), PreconstructionContentSnapshot.id.desc())


def _snapshot_for_run(db: Session, run_id: int) -> PreconstructionContentSnapshot | None:
    return db.query(PreconstructionContentSnapshot).filter(
        PreconstructionContentSnapshot.preparation_run_id == run_id
    ).first()


def preparation_run_response(db: Session, run: PreconstructionPreparationRun) -> dict:
    snapshot = _snapshot_for_run(db, run.id)
    extraction = db.get(DocumentExtraction, run.extraction_id) if run.extraction_id else None
    return {
        "run_id": run.id,
        "source_id": run.review_source_id,
        "status": run.status,
        "lineage_fingerprint": run.lineage_fingerprint,
        "source_checksum": run.source_checksum,
        "extraction_status": extraction.status if extraction else "unavailable",
        "extraction_method": run.extraction_method,
        "extractor_version": run.extractor_version,
        "preparation_version": run.preparation_version,
        "requested_at": run.requested_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "failed_at": run.failed_at,
        "cancelled_at": run.cancelled_at,
        "attempt_count": run.attempt_count,
        "max_attempts": run.max_attempts,
        "snapshot_id": snapshot.id if snapshot else None,
        "page_count": snapshot.page_count if snapshot else 0,
        "segment_count": snapshot.segment_count if snapshot else 0,
        "total_character_count": snapshot.total_character_count if snapshot else 0,
        "warning_count": snapshot.warning_count if snapshot else run.warning_count,
        "failure_code": run.failure_code,
        "failure_message": run.failure_message,
        "can_cancel": run.status in ACTIVE_PREPARATION_STATUSES,
        "can_retry": run.status == "failed" and run.attempt_count < run.max_attempts,
    }


def request_source_preparation(
    db: Session,
    review_set: PreconstructionReviewSet,
    source: PreconstructionReviewSource,
    requested_by: int,
    config: PreconstructionPreparationConfig,
) -> PreconstructionPreparationRun:
    if review_set.status == "archived":
        raise _conflict("Archived preconstruction review sets are read-only")
    eligibility = evaluate_preparation_eligibility(db, source, config)
    fingerprint = eligibility.fingerprint or _canonical_hash({
        "document_checksum": source.source_checksum,
        "source_id": source.id,
        "preparation_version": config.preparation_version,
        "segmentation_policy_version": config.segmentation_policy_version,
        "eligibility_code": eligibility.code,
    })
    completed = db.query(PreconstructionContentSnapshot).filter(
        PreconstructionContentSnapshot.review_source_id == source.id,
        PreconstructionContentSnapshot.lineage_fingerprint == fingerprint,
        PreconstructionContentSnapshot.status.in_(COMPLETED_SNAPSHOT_STATUSES),
    ).first()
    if completed:
        return db.get(PreconstructionPreparationRun, completed.preparation_run_id)
    active = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.review_source_id == source.id,
        PreconstructionPreparationRun.lineage_fingerprint == fingerprint,
        PreconstructionPreparationRun.status.in_(ACTIVE_PREPARATION_STATUSES),
    ).first()
    if active:
        return active
    extraction = eligibility.extraction
    run = PreconstructionPreparationRun(
        project_id=source.project_id,
        review_source_id=source.id,
        status="pending" if eligibility.eligible else "unavailable",
        source_checksum=source.source_checksum,
        lineage_fingerprint=fingerprint,
        extraction_id=extraction.id if extraction else None,
        extraction_method=extraction.extraction_method if extraction else "unavailable",
        extractor_version=extraction.extractor_version if extraction else "unavailable",
        extraction_completed_at=extraction.completed_at if extraction else None,
        renderer_version=None,
        preparation_version=config.preparation_version,
        segmentation_policy_version=config.segmentation_policy_version,
        attempt_count=0,
        max_attempts=config.max_attempts,
        requested_by=requested_by,
        failure_code=eligibility.code,
        failure_message=eligibility.message,
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(PreconstructionPreparationRun).filter(
            PreconstructionPreparationRun.review_source_id == source.id,
            PreconstructionPreparationRun.lineage_fingerprint == fingerprint,
            PreconstructionPreparationRun.status.in_(ACTIVE_PREPARATION_STATUSES),
        ).first()
        if existing:
            return existing
        raise
    db.refresh(run)
    return run


def get_preparation_run(db: Session, project_id: int, run_id: int) -> PreconstructionPreparationRun:
    run = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.id == run_id,
        PreconstructionPreparationRun.project_id == project_id,
    ).first()
    if run is None:
        raise _not_found("Preconstruction preparation run not found")
    return run


def cancel_preparation_run(db: Session, run: PreconstructionPreparationRun) -> PreconstructionPreparationRun:
    if run.status not in ACTIVE_PREPARATION_STATUSES:
        raise _conflict("Only pending or processing preparation runs can be cancelled")
    now = utc_now()
    run.status = "cancelled"
    run.cancelled_at = now
    run.lease_token_digest = None
    run.lease_expires_at = None
    run.updated_at = now
    db.commit()
    db.refresh(run)
    return run


def retry_preparation_run(
    db: Session,
    run: PreconstructionPreparationRun,
) -> PreconstructionPreparationRun:
    if run.status != "failed":
        raise _conflict("Only failed preparation runs can be retried")
    if run.attempt_count >= run.max_attempts:
        raise _conflict("Preparation run has reached its retry limit")
    run.status = "pending"
    run.available_at = utc_now()
    run.failed_at = None
    run.failure_code = None
    run.failure_message = None
    run.updated_at = utc_now()
    db.commit()
    db.refresh(run)
    return run


@dataclass(frozen=True)
class ClaimedPreparationRun:
    run_id: int
    lease_token: str


@dataclass
class PreparationProcessingResult:
    claimed: int = 0
    completed: int = 0
    warnings: int = 0
    unavailable: int = 0
    retryable: int = 0
    failed: int = 0
    cancelled: int = 0
    skipped: int = 0


class PreparationError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool = False, unavailable: bool = False):
        super().__init__(_safe_message(code))
        self.code = code
        self.retryable = retryable
        self.unavailable = unavailable


def _retry_delay(config: PreconstructionPreparationConfig, attempt_count: int) -> int:
    return min(config.retry_base_seconds * (2 ** max(attempt_count - 1, 0)), config.retry_max_seconds)


def recover_expired_preparation_runs(db: Session, config: PreconstructionPreparationConfig) -> int:
    now = utc_now()
    runs = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.status == "processing",
        PreconstructionPreparationRun.lease_expires_at.is_not(None),
        PreconstructionPreparationRun.lease_expires_at <= now,
    ).with_for_update().all()
    for run in runs:
        run.lease_token_digest = None
        run.lease_expires_at = None
        run.failure_code = "lease_expired"
        run.failure_message = _safe_message("lease_expired")
        if run.attempt_count >= run.max_attempts:
            run.status = "failed"
            run.failed_at = now
        else:
            run.status = "pending"
            run.available_at = now + timedelta(seconds=_retry_delay(config, run.attempt_count))
        run.updated_at = now
    if runs:
        db.commit()
    return len(runs)


def claim_preparation_run(
    db: Session,
    *,
    run_id: int | None = None,
    lease_seconds: int,
) -> ClaimedPreparationRun | None:
    now = utc_now()
    query = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.status == "pending",
        PreconstructionPreparationRun.available_at <= now,
    )
    if run_id is not None:
        query = query.filter(PreconstructionPreparationRun.id == run_id)
    query = query.order_by(
        PreconstructionPreparationRun.available_at.asc(),
        PreconstructionPreparationRun.requested_at.asc(),
        PreconstructionPreparationRun.id.asc(),
    )
    if db.get_bind().dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    else:
        query = query.with_for_update()
    run = query.first()
    if run is None:
        db.rollback()
        return None
    token = uuid.uuid4().hex
    run.status = "processing"
    run.attempt_count += 1
    run.started_at = run.started_at or now
    run.lease_token_digest = sha256(token.encode("ascii")).hexdigest()
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    run.updated_at = now
    db.commit()
    return ClaimedPreparationRun(run.id, token)


def sanitize_content_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return "".join(
        character
        for character in normalized
        if character in {"\n", "\t"} or unicodedata.category(character) not in {"Cc", "Cf"}
    )


def normalized_segment_text(value: str) -> str:
    return " ".join(value.casefold().split())


def segment_page_text(text: str, maximum: int) -> list[tuple[str, int, int]]:
    if not text or not text.strip():
        return []
    segments = []
    cursor = 0
    length = len(text)
    while cursor < length:
        end = min(cursor + maximum, length)
        if end < length:
            minimum_break = cursor + maximum // 2
            candidates = (
                text.rfind("\n\n", minimum_break, end),
                text.rfind("\n", minimum_break, end),
                text.rfind(" ", minimum_break, end),
            )
            boundary = next((candidate for candidate in candidates if candidate > cursor), -1)
            if boundary > cursor:
                end = boundary + (2 if text[boundary:boundary + 2] == "\n\n" else 1)
        piece = text[cursor:end]
        if piece:
            segments.append((piece, cursor, end))
        cursor = end
    return segments


def _content_hash(page_rows: list[dict], segment_rows: list[dict]) -> str:
    return _canonical_hash({
        "pages": [
            {"page_number": page["page_number"], "text_hash": page["page_text_hash"]}
            for page in page_rows
        ],
        "segments": [
            {
                "page_number": segment["page_number"],
                "segment_index": segment["segment_index"],
                "text_hash": segment["text_hash"],
            }
            for segment in segment_rows
        ],
    })


def _record_processing_failure(
    db: Session,
    claim: ClaimedPreparationRun,
    error: PreparationError,
    config: PreconstructionPreparationConfig,
) -> str:
    db.rollback()
    digest = sha256(claim.lease_token.encode("ascii")).hexdigest()
    run = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.id == claim.run_id,
        PreconstructionPreparationRun.status == "processing",
        PreconstructionPreparationRun.lease_token_digest == digest,
    ).with_for_update().first()
    if run is None:
        db.rollback()
        return "skipped"
    now = utc_now()
    run.lease_token_digest = None
    run.lease_expires_at = None
    run.failure_code = error.code
    run.failure_message = _safe_message(error.code)
    if error.unavailable:
        run.status = "unavailable"
        run.failed_at = now
        result = "unavailable"
    elif error.retryable and run.attempt_count < run.max_attempts:
        run.status = "pending"
        run.available_at = now + timedelta(seconds=_retry_delay(config, run.attempt_count))
        result = "retryable"
    else:
        run.status = "failed"
        run.failed_at = now
        result = "failed"
    run.updated_at = now
    db.commit()
    return result


def process_preparation_claim(
    db: Session,
    claim: ClaimedPreparationRun,
    config: PreconstructionPreparationConfig,
) -> str:
    digest = sha256(claim.lease_token.encode("ascii")).hexdigest()
    run = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.id == claim.run_id,
        PreconstructionPreparationRun.status == "processing",
        PreconstructionPreparationRun.lease_token_digest == digest,
    ).first()
    if run is None:
        return "skipped"
    source = db.get(PreconstructionReviewSource, run.review_source_id)
    if source is None or source.removed_at is not None:
        return _record_processing_failure(db, claim, PreparationError("document_unavailable", unavailable=True), config)
    eligibility = evaluate_preparation_eligibility(db, source, config)
    if not eligibility.eligible:
        return _record_processing_failure(db, claim, PreparationError(eligibility.code or "preparation_failed", unavailable=True), config)
    if eligibility.fingerprint != run.lineage_fingerprint:
        return _record_processing_failure(db, claim, PreparationError("source_lineage_changed"), config)
    pages = db.query(DocumentPageText).filter(
        DocumentPageText.project_id == run.project_id,
        DocumentPageText.extraction_id == run.extraction_id,
    ).order_by(DocumentPageText.page_number.asc(), DocumentPageText.id.asc()).all()
    try:
        page_rows = []
        page_segments: list[list[tuple[str, str, int, int, str, int | None]]] = []
        warning_codes = set(eligibility.warning_codes)
        total_characters = 0
        total_segments = 0
        for page in pages:
            clean_text = sanitize_content_text(page.text)
            total_characters += len(clean_text)
            if total_characters > config.max_total_characters:
                raise PreparationError("text_limit_exceeded", unavailable=True)
            split = segment_page_text(clean_text, config.max_segment_characters)
            total_segments += len(split)
            if total_segments > config.max_segments:
                raise PreparationError("segment_limit_exceeded", unavailable=True)
            if not split:
                warning_codes.add("empty_page")
            page_rows.append({
                "project_id": run.project_id,
                "page_number": page.page_number,
                "page_label": None,
                "sheet_number": source.sheet_number_snapshot,
                "width_points": None,
                "height_points": None,
                "rotation": None,
                "extraction_method": page.extraction_method,
                "character_count": len(clean_text),
                "page_text_hash": sha256(clean_text.encode("utf-8")).hexdigest(),
                "has_searchable_text": bool(clean_text.strip()),
                "has_visual_content": False,
                "warning_codes": json.dumps(["empty_page"]) if not split else None,
                "created_at": utc_now(),
            })
            page_segments.append([
                (
                    piece,
                    normalized_segment_text(piece),
                    start,
                    end,
                    sha256(piece.encode("utf-8")).hexdigest(),
                    int(page.confidence) if page.confidence is not None else None,
                )
                for piece, start, end in split
            ])
        if not total_segments:
            raise PreparationError("no_searchable_text", unavailable=True)
        now = utc_now()
        snapshot = PreconstructionContentSnapshot(
            project_id=run.project_id,
            review_source_id=source.id,
            document_id=source.document_id,
            drawing_revision_id=source.drawing_revision_id,
            source_checksum=run.source_checksum,
            extraction_id=run.extraction_id,
            extraction_method=run.extraction_method,
            extractor_version=run.extractor_version,
            extraction_completed_at=run.extraction_completed_at,
            renderer_version=run.renderer_version,
            preparation_version=run.preparation_version,
            segmentation_policy_version=run.segmentation_policy_version,
            lineage_fingerprint=run.lineage_fingerprint,
            status="processing",
            page_count=len(page_rows),
            segment_count=total_segments,
            total_character_count=total_characters,
            content_hash="0" * 64,
            preparation_run_id=run.id,
            warning_count=len(warning_codes),
            warning_codes=json.dumps(sorted(warning_codes)) if warning_codes else None,
            created_at=now,
        )
        db.add(snapshot)
        db.flush()
        for page_row in page_rows:
            page_row["snapshot_id"] = snapshot.id
        inserted_pages = db.execute(
            insert(PreconstructionContentPage).returning(
                PreconstructionContentPage.id,
                PreconstructionContentPage.page_number,
            ),
            page_rows,
        ).all()
        page_ids = {page_number: page_id for page_id, page_number in inserted_pages}
        segment_rows = []
        for page_row, items in zip(page_rows, page_segments):
            for index, (text, normalized, start, end, text_hash, confidence) in enumerate(items):
                segment_rows.append({
                    "project_id": run.project_id,
                    "snapshot_id": snapshot.id,
                    "page_id": page_ids[page_row["page_number"]],
                    "page_number": page_row["page_number"],
                    "segment_index": index,
                    "segment_type": "page_text",
                    "text": text,
                    "normalized_text": normalized,
                    "text_hash": text_hash,
                    "character_start": start,
                    "character_end": end,
                    "token_estimate": (len(normalized) + 3) // 4,
                    "heading_path": None,
                    "bounding_box": None,
                    "extraction_method": page_row["extraction_method"],
                    "confidence": confidence,
                    "created_at": now,
                })
        insert_rows = [
            {key: value for key, value in item.items() if key != "page_number"}
            for item in segment_rows
        ]
        db.execute(insert(PreconstructionContentSegment), insert_rows)
        if len(page_rows) != snapshot.page_count or len(segment_rows) != snapshot.segment_count:
            raise PreparationError("preparation_failed")
        snapshot.content_hash = _content_hash(page_rows, segment_rows)
        snapshot.status = "completed_with_warnings" if warning_codes else "completed"
        snapshot.completed_at = now
        locked_run = db.query(PreconstructionPreparationRun).filter(
            PreconstructionPreparationRun.id == run.id,
            PreconstructionPreparationRun.status == "processing",
            PreconstructionPreparationRun.lease_token_digest == digest,
        ).with_for_update().first()
        if locked_run is None:
            db.rollback()
            return "cancelled"
        locked_run.status = snapshot.status
        locked_run.completed_at = now
        locked_run.failure_code = None
        locked_run.failure_message = None
        locked_run.warning_count = len(warning_codes)
        locked_run.lease_token_digest = None
        locked_run.lease_expires_at = None
        locked_run.updated_at = now
        db.commit()
        return "warnings" if warning_codes else "completed"
    except PreparationError as error:
        return _record_processing_failure(db, claim, error, config)
    except Exception:
        return _record_processing_failure(db, claim, PreparationError("preparation_failed", retryable=True), config)


def process_preparation_runs(
    db: Session,
    config: PreconstructionPreparationConfig,
    *,
    batch_size: int | None = None,
    max_jobs: int | None = None,
    run_id: int | None = None,
    lease_seconds: int | None = None,
) -> PreparationProcessingResult:
    result = PreparationProcessingResult()
    recover_expired_preparation_runs(db, config)
    limit = max_jobs or batch_size or config.batch_size
    for _ in range(limit):
        claim = claim_preparation_run(
            db,
            run_id=run_id,
            lease_seconds=lease_seconds or config.lease_seconds,
        )
        if claim is None:
            break
        result.claimed += 1
        outcome = process_preparation_claim(db, claim, config)
        setattr(result, outcome, getattr(result, outcome) + 1)
        if run_id is not None:
            break
    return result


def _state_for_source(
    source: PreconstructionReviewSource,
    document: Document | None,
    extraction: DocumentExtraction | None,
    snapshot: PreconstructionContentSnapshot | None,
    run: PreconstructionPreparationRun | None,
    config: PreconstructionPreparationConfig,
) -> dict:
    current_fingerprint = None
    stale_reason = None
    if document is None or document.deleted_at is not None or source.removed_at is not None:
        stale_reason = "Source document is unavailable"
    elif document.checksum_sha256 != source.source_checksum:
        stale_reason = "Document checksum changed"
    elif extraction is None:
        stale_reason = "Extraction is unavailable"
    elif extraction.source_checksum != document.checksum_sha256:
        stale_reason = "Extraction checksum changed"
    else:
        current_fingerprint = lineage_fingerprint(source, document, extraction, config)
        if snapshot and snapshot.lineage_fingerprint != current_fingerprint:
            stale_reason = "Extraction or preparation version changed"
    lineage_current = bool(snapshot and current_fingerprint == snapshot.lineage_fingerprint and not stale_reason)
    if snapshot and not lineage_current:
        preparation_status = "stale"
    elif snapshot:
        preparation_status = "ready_with_warnings" if snapshot.status == "completed_with_warnings" else "ready"
    elif run and run.status in ("pending", "processing", "failed", "unavailable", "cancelled"):
        preparation_status = run.status
    else:
        preparation_status = "not_prepared"
    return {
        "preparation_status": preparation_status,
        "preparation_run_id": run.id if run else (snapshot.preparation_run_id if snapshot else None),
        "content_snapshot_id": snapshot.id if snapshot else None,
        "prepared_at": snapshot.completed_at if snapshot else None,
        "page_count": snapshot.page_count if snapshot else 0,
        "segment_count": snapshot.segment_count if snapshot else 0,
        "total_character_count": snapshot.total_character_count if snapshot else 0,
        "preparation_extraction_method": snapshot.extraction_method if snapshot else (extraction.extraction_method if extraction else None),
        "warning_count": snapshot.warning_count if snapshot else (run.warning_count if run else 0),
        "unavailable_reason": run.failure_message if run and run.status == "unavailable" else None,
        "lineage_current": lineage_current,
        "stale_reason": stale_reason,
        "current_extraction_status": extraction.status if extraction else "not_processed",
        "lineage_fingerprint": snapshot.lineage_fingerprint if snapshot else None,
        "content_hash": snapshot.content_hash if snapshot else None,
        "preparation_version": snapshot.preparation_version if snapshot else None,
        "segmentation_policy_version": snapshot.segmentation_policy_version if snapshot else None,
        "snapshot_extraction_method": snapshot.extraction_method if snapshot else None,
        "snapshot_extractor_version": snapshot.extractor_version if snapshot else None,
    }


def source_preparation_states(
    db: Session,
    sources: list[PreconstructionReviewSource],
    config: PreconstructionPreparationConfig,
) -> dict[int, dict]:
    if not sources:
        return {}
    project_id = sources[0].project_id
    document_ids = sorted({source.document_id for source in sources})
    source_ids = [source.id for source in sources]
    documents = db.query(Document).filter(
        Document.project_id == project_id, Document.id.in_(document_ids)
    ).all()
    extractions = db.query(DocumentExtraction).filter(
        DocumentExtraction.project_id == project_id,
        DocumentExtraction.document_id.in_(document_ids),
    ).all()
    snapshots = db.query(PreconstructionContentSnapshot).filter(
        PreconstructionContentSnapshot.project_id == project_id,
        PreconstructionContentSnapshot.review_source_id.in_(source_ids),
        PreconstructionContentSnapshot.status.in_(COMPLETED_SNAPSHOT_STATUSES),
    ).order_by(PreconstructionContentSnapshot.created_at.desc(), PreconstructionContentSnapshot.id.desc()).all()
    runs = db.query(PreconstructionPreparationRun).filter(
        PreconstructionPreparationRun.project_id == project_id,
        PreconstructionPreparationRun.review_source_id.in_(source_ids),
    ).order_by(PreconstructionPreparationRun.requested_at.desc(), PreconstructionPreparationRun.id.desc()).all()
    documents_by_id = {item.id: item for item in documents}
    extractions_by_document = {item.document_id: item for item in extractions}
    snapshot_by_source = {}
    for item in snapshots:
        snapshot_by_source.setdefault(item.review_source_id, item)
    run_by_source = {}
    for item in runs:
        run_by_source.setdefault(item.review_source_id, item)
    return {
        source.id: _state_for_source(
            source,
            documents_by_id.get(source.document_id),
            extractions_by_document.get(source.document_id),
            snapshot_by_source.get(source.id),
            run_by_source.get(source.id),
            config,
        )
        for source in sources
    }


def get_content_snapshot(
    db: Session,
    project_id: int,
    source: PreconstructionReviewSource,
    snapshot_id: int | None = None,
) -> PreconstructionContentSnapshot:
    query = db.query(PreconstructionContentSnapshot).filter(
        PreconstructionContentSnapshot.project_id == project_id,
        PreconstructionContentSnapshot.review_source_id == source.id,
        PreconstructionContentSnapshot.status.in_(COMPLETED_SNAPSHOT_STATUSES),
    )
    if snapshot_id is not None:
        query = query.filter(PreconstructionContentSnapshot.id == snapshot_id)
    snapshot = query.order_by(
        PreconstructionContentSnapshot.created_at.desc(),
        PreconstructionContentSnapshot.id.desc(),
    ).first()
    if snapshot is None:
        raise _not_found("Prepared source content not found")
    return snapshot


def retrieve_snapshot_segments(
    db: Session,
    project_id: int,
    snapshot_id: int,
    *,
    page_number: int | None = None,
    segment_ids: list[int] | None = None,
    max_characters: int,
) -> list[PreconstructionContentSegment]:
    query = db.query(PreconstructionContentSegment).join(
        PreconstructionContentPage,
        PreconstructionContentPage.id == PreconstructionContentSegment.page_id,
    ).filter(
        PreconstructionContentSegment.project_id == project_id,
        PreconstructionContentSegment.snapshot_id == snapshot_id,
    )
    if page_number is not None:
        query = query.filter(PreconstructionContentPage.page_number == page_number)
    if segment_ids is not None:
        query = query.filter(PreconstructionContentSegment.id.in_(segment_ids))
    items = query.order_by(
        PreconstructionContentPage.page_number.asc(),
        PreconstructionContentSegment.segment_index.asc(),
        PreconstructionContentSegment.id.asc(),
    ).all()
    selected = []
    characters = 0
    for item in items:
        if characters + len(item.text) > max_characters:
            break
        selected.append(item)
        characters += len(item.text)
    return selected


def inspect_source_content(
    db: Session,
    source: PreconstructionReviewSource,
    config: PreconstructionPreparationConfig,
    *,
    snapshot_id: int | None,
    page_number: int | None,
    segment_offset: int,
    segment_limit: int,
    search: str,
) -> dict:
    snapshot = get_content_snapshot(db, source.project_id, source, snapshot_id)
    pages = db.query(PreconstructionContentPage).filter(
        PreconstructionContentPage.project_id == source.project_id,
        PreconstructionContentPage.snapshot_id == snapshot.id,
    ).order_by(PreconstructionContentPage.page_number.asc()).all()
    query = db.query(PreconstructionContentSegment, PreconstructionContentPage.page_number).join(
        PreconstructionContentPage,
        PreconstructionContentPage.id == PreconstructionContentSegment.page_id,
    ).filter(
        PreconstructionContentSegment.project_id == source.project_id,
        PreconstructionContentSegment.snapshot_id == snapshot.id,
    )
    if page_number is not None:
        query = query.filter(PreconstructionContentPage.page_number == page_number)
    normalized_search = normalized_segment_text(sanitize_content_text(search))
    if normalized_search:
        query = query.filter(PreconstructionContentSegment.normalized_text.contains(normalized_search))
    total = query.with_entities(func.count(PreconstructionContentSegment.id)).scalar()
    rows = query.order_by(
        PreconstructionContentPage.page_number.asc(),
        PreconstructionContentSegment.segment_index.asc(),
        PreconstructionContentSegment.id.asc(),
    ).offset(segment_offset).limit(segment_limit).all()
    segment_items = []
    response_characters = 0
    truncated = False
    for segment, item_page_number in rows:
        if response_characters + len(segment.text) > config.content_max_response_characters:
            truncated = True
            break
        response_characters += len(segment.text)
        segment_items.append({
            "id": segment.id,
            "page_number": item_page_number,
            "segment_index": segment.segment_index,
            "segment_type": segment.segment_type,
            "text": segment.text,
            "text_hash": segment.text_hash,
            "character_start": segment.character_start,
            "character_end": segment.character_end,
            "token_estimate": segment.token_estimate,
            "heading_path": segment.heading_path,
            "bounding_box": json.loads(segment.bounding_box) if segment.bounding_box else None,
            "extraction_method": segment.extraction_method,
            "confidence": float(segment.confidence) if segment.confidence is not None else None,
        })
    revision = db.get(DrawingRevision, source.drawing_revision_id) if source.drawing_revision_id else None
    sheet = db.get(DrawingSheet, revision.drawing_sheet_id) if revision else None
    route_target = (
        {"page": "drawingViewer", "projectId": source.project_id, "sheetId": sheet.id, "revisionId": revision.id}
        if revision and sheet
        else {"page": "projectDocuments", "projectId": source.project_id, "documentId": source.document_id}
    )
    current_document = db.get(Document, source.document_id)
    current_extraction = db.query(DocumentExtraction).filter(
        DocumentExtraction.document_id == source.document_id
    ).first()
    current_fingerprint = (
        lineage_fingerprint(source, current_document, current_extraction, config)
        if (
            current_document
            and current_document.deleted_at is None
            and current_document.checksum_sha256 == source.source_checksum
            and current_extraction
            and current_extraction.source_checksum == current_document.checksum_sha256
        )
        else None
    )
    return {
        "source": {
            "id": source.id,
            "display_name": source.display_name_snapshot,
            "source_type": source.source_type,
            "document_id": source.document_id,
            "drawing_revision_id": source.drawing_revision_id,
            "sheet_number": source.sheet_number_snapshot,
            "revision_code": source.revision_code_snapshot,
            "route_target": route_target,
        },
        "snapshot": {
            "id": snapshot.id,
            "source_checksum": snapshot.source_checksum,
            "lineage_fingerprint": snapshot.lineage_fingerprint,
            "lineage_current": snapshot.lineage_fingerprint == current_fingerprint,
            "content_hash": snapshot.content_hash,
            "extraction_method": snapshot.extraction_method,
            "extractor_version": snapshot.extractor_version,
            "preparation_version": snapshot.preparation_version,
            "segmentation_policy_version": snapshot.segmentation_policy_version,
            "status": snapshot.status,
            "page_count": snapshot.page_count,
            "segment_count": snapshot.segment_count,
            "total_character_count": snapshot.total_character_count,
            "warning_count": snapshot.warning_count,
            "created_at": snapshot.created_at,
            "completed_at": snapshot.completed_at,
        },
        "pages": [{
            "id": page.id,
            "page_number": page.page_number,
            "page_label": page.page_label,
            "sheet_number": page.sheet_number,
            "character_count": page.character_count,
            "page_text_hash": page.page_text_hash,
            "has_searchable_text": page.has_searchable_text,
            "has_visual_content": page.has_visual_content,
            "extraction_method": page.extraction_method,
        } for page in pages],
        "segments": segment_items,
        "pagination": {
            "offset": segment_offset,
            "limit": segment_limit,
            "total": total,
            "response_character_count": response_characters,
            "response_truncated": truncated,
        },
    }
