from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.attachment import Attachment
from app.models.attachment_cleanup import AttachmentCleanupJob
from app.storage.attachment import (
    AttachmentObjectMissing,
    AttachmentStorage,
    AttachmentStorageError,
)


logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("Pending", "Processing", "Failed")
MAX_ERROR_LENGTH = 500
StorageResolver = Callable[[str], AttachmentStorage]


@dataclass(frozen=True)
class CleanupPlan:
    attachment_count: int
    job_ids: tuple[int, ...]


@dataclass
class CleanupProcessingResult:
    claimed: int = 0
    completed: int = 0
    retryable: int = 0
    failed: int = 0


@dataclass
class ReconciliationReport:
    metadata_present: int = 0
    metadata_missing: int = 0
    metadata_unavailable: int = 0
    cleanup_present: int = 0
    cleanup_missing: int = 0
    cleanup_unavailable: int = 0
    completed_retained: int = 0
    completed_prunable: int = 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_error_summary(error: AttachmentStorageError) -> str:
    category = getattr(error, "category", "unknown")
    summary = f"{category}: attachment storage operation failed"
    return summary[:MAX_ERROR_LENGTH]


def enqueue_cleanup_job(
    db: Session,
    *,
    attachment_id: int | None,
    project_id: int,
    storage_provider: str,
    storage_key: str,
) -> AttachmentCleanupJob:
    existing = (
        db.query(AttachmentCleanupJob)
        .filter(
            AttachmentCleanupJob.storage_provider
            == storage_provider,
            AttachmentCleanupJob.storage_key == storage_key,
            AttachmentCleanupJob.status.in_(ACTIVE_STATUSES),
        )
        .first()
    )
    if existing is not None:
        return existing

    job = AttachmentCleanupJob(
        attachment_id=attachment_id,
        project_id=project_id,
        storage_provider=storage_provider,
        storage_key=storage_key,
    )
    db.add(job)
    db.flush()
    logger.info(
        "Queued attachment cleanup job %s for project %s using %s",
        job.id,
        project_id,
        storage_provider,
    )
    return job


def queue_attachments_for_cleanup(
    db: Session,
    attachments: Iterable[Attachment],
) -> CleanupPlan:
    job_ids: list[int] = []
    attachment_count = 0
    for attachment in attachments:
        job = enqueue_cleanup_job(
            db,
            attachment_id=attachment.id,
            project_id=attachment.project_id,
            storage_provider=attachment.storage_provider,
            storage_key=attachment.storage_key,
        )
        job_ids.append(job.id)
        db.delete(attachment)
        attachment_count += 1
    return CleanupPlan(attachment_count, tuple(job_ids))


def queue_project_attachments_for_cleanup(
    db: Session,
    project_id: int,
    *,
    batch_size: int,
) -> CleanupPlan:
    job_ids: list[int] = []
    attachment_count = 0
    last_id = 0

    while True:
        attachments = (
            db.query(Attachment)
            .filter(
                Attachment.project_id == project_id,
                Attachment.id > last_id,
            )
            .order_by(Attachment.id.asc())
            .limit(batch_size)
            .all()
        )
        if not attachments:
            break
        last_id = attachments[-1].id
        plan = queue_attachments_for_cleanup(db, attachments)
        job_ids.extend(plan.job_ids)
        attachment_count += plan.attachment_count
        db.flush()

    return CleanupPlan(attachment_count, tuple(job_ids))


def _retry_delay(
    config: AttachmentConfig,
    attempt_count: int,
) -> int:
    delay = config.cleanup_retry_base_seconds * (
        2 ** max(attempt_count - 1, 0)
    )
    return min(delay, config.cleanup_retry_max_seconds)


def _complete_job(
    db: Session,
    job: AttachmentCleanupJob,
    now: datetime,
) -> None:
    job.status = "Completed"
    job.last_error = None
    job.completed_at = now
    job.updated_at = now
    db.commit()


def _record_failure(
    db: Session,
    job: AttachmentCleanupJob,
    error: AttachmentStorageError,
    config: AttachmentConfig,
    now: datetime,
) -> str:
    can_retry = (
        error.retryable
        and job.attempt_count < config.cleanup_max_attempts
    )
    job.status = "Pending" if can_retry else "Failed"
    job.last_error = safe_error_summary(error)
    job.next_attempt_at = now + timedelta(
        seconds=_retry_delay(config, job.attempt_count)
    )
    job.updated_at = now
    db.commit()
    logger.warning(
        "Attachment cleanup job %s ended with %s storage failure",
        job.id,
        error.category,
    )
    return job.status


def _execute_job(
    db: Session,
    job_id: int,
    storage: AttachmentStorage,
    config: AttachmentConfig,
) -> str:
    job = db.get(AttachmentCleanupJob, job_id)
    if job is None or job.status != "Processing":
        return "Skipped"

    now = utc_now()
    try:
        storage.delete(job.storage_key)
    except AttachmentObjectMissing:
        _complete_job(db, job, now)
        return "Completed"
    except AttachmentStorageError as error:
        return _record_failure(db, job, error, config, now)

    _complete_job(db, job, now)
    return "Completed"


def claim_cleanup_jobs(
    db: Session,
    *,
    batch_size: int,
    lease_seconds: int,
    now: datetime | None = None,
) -> tuple[int, ...]:
    current_time = now or utc_now()
    lease_expired_at = current_time - timedelta(
        seconds=lease_seconds
    )

    (
        db.query(AttachmentCleanupJob)
        .filter(
            AttachmentCleanupJob.status == "Processing",
            AttachmentCleanupJob.updated_at <= lease_expired_at,
        )
        .update(
            {
                AttachmentCleanupJob.status: "Pending",
                AttachmentCleanupJob.next_attempt_at: current_time,
                AttachmentCleanupJob.updated_at: current_time,
            },
            synchronize_session=False,
        )
    )

    jobs = (
        db.query(AttachmentCleanupJob)
        .filter(
            AttachmentCleanupJob.status == "Pending",
            AttachmentCleanupJob.next_attempt_at <= current_time,
        )
        .order_by(
            AttachmentCleanupJob.next_attempt_at.asc(),
            AttachmentCleanupJob.created_at.asc(),
            AttachmentCleanupJob.id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    for job in jobs:
        job.status = "Processing"
        job.attempt_count += 1
        job.updated_at = current_time
    db.commit()
    return tuple(job.id for job in jobs)


def process_cleanup_job_ids(
    db: Session,
    job_ids: Iterable[int],
    storage: AttachmentStorage,
    config: AttachmentConfig,
) -> CleanupProcessingResult:
    ids = tuple(dict.fromkeys(job_ids))
    if not ids:
        return CleanupProcessingResult()

    now = utc_now()
    jobs = (
        db.query(AttachmentCleanupJob)
        .filter(
            AttachmentCleanupJob.id.in_(ids),
            AttachmentCleanupJob.status == "Pending",
            AttachmentCleanupJob.storage_provider
            == storage.provider_name,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for job in jobs:
        job.status = "Processing"
        job.attempt_count += 1
        job.updated_at = now
    db.commit()

    result = CleanupProcessingResult(claimed=len(jobs))
    for job in jobs:
        outcome = _execute_job(db, job.id, storage, config)
        if outcome == "Completed":
            result.completed += 1
        elif outcome == "Pending":
            result.retryable += 1
        elif outcome == "Failed":
            result.failed += 1
    return result


def process_cleanup_jobs(
    db: Session,
    storage_resolver: StorageResolver,
    config: AttachmentConfig,
    *,
    batch_size: int | None = None,
    max_jobs: int | None = None,
) -> CleanupProcessingResult:
    configured_batch = batch_size or config.cleanup_batch_size
    remaining = max_jobs or configured_batch
    result = CleanupProcessingResult()

    while remaining > 0:
        claim_size = min(configured_batch, remaining)
        job_ids = claim_cleanup_jobs(
            db,
            batch_size=claim_size,
            lease_seconds=config.cleanup_lease_seconds,
        )
        if not job_ids:
            break
        result.claimed += len(job_ids)
        remaining -= len(job_ids)

        for job_id in job_ids:
            job = db.get(AttachmentCleanupJob, job_id)
            if job is None:
                continue
            try:
                storage = storage_resolver(job.storage_provider)
            except AttachmentStorageError as error:
                outcome = _record_failure(
                    db,
                    job,
                    error,
                    config,
                    utc_now(),
                )
            else:
                outcome = _execute_job(
                    db,
                    job_id,
                    storage,
                    config,
                )

            if outcome == "Completed":
                result.completed += 1
            elif outcome == "Pending":
                result.retryable += 1
            elif outcome == "Failed":
                result.failed += 1

    return result


def prune_completed_cleanup_jobs(
    db: Session,
    config: AttachmentConfig,
    *,
    now: datetime | None = None,
) -> int:
    cutoff = (now or utc_now()) - timedelta(
        days=config.cleanup_retention_days
    )
    count = (
        db.query(AttachmentCleanupJob)
        .filter(
            AttachmentCleanupJob.status == "Completed",
            AttachmentCleanupJob.completed_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return count


def reconcile_attachment_storage(
    db: Session,
    storage_resolver: StorageResolver,
    config: AttachmentConfig,
    *,
    now: datetime | None = None,
) -> ReconciliationReport:
    report = ReconciliationReport()

    for attachment in db.query(Attachment).yield_per(
        config.cleanup_batch_size
    ):
        try:
            exists = storage_resolver(
                attachment.storage_provider
            ).exists(attachment.storage_key)
        except AttachmentStorageError:
            report.metadata_unavailable += 1
        else:
            if exists:
                report.metadata_present += 1
            else:
                report.metadata_missing += 1

    jobs = (
        db.query(AttachmentCleanupJob)
        .filter(AttachmentCleanupJob.status.in_(ACTIVE_STATUSES))
        .yield_per(config.cleanup_batch_size)
    )
    for job in jobs:
        try:
            exists = storage_resolver(
                job.storage_provider
            ).exists(job.storage_key)
        except AttachmentStorageError:
            report.cleanup_unavailable += 1
        else:
            if exists:
                report.cleanup_present += 1
            else:
                report.cleanup_missing += 1

    cutoff = (now or utc_now()) - timedelta(
        days=config.cleanup_retention_days
    )
    completed = db.query(AttachmentCleanupJob).filter(
        AttachmentCleanupJob.status == "Completed"
    )
    report.completed_prunable = completed.filter(
        AttachmentCleanupJob.completed_at < cutoff
    ).count()
    report.completed_retained = completed.filter(
        AttachmentCleanupJob.completed_at >= cutoff
    ).count()
    return report
