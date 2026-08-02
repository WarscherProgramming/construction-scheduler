import argparse
from collections.abc import Callable, Sequence

from app.core.config import (
    ATTACHMENT_CONFIG,
    DOCUMENT_EXTRACTION_CONFIG,
    AttachmentConfig,
    DocumentExtractionConfig,
)
from app.db.database import SessionLocal
from app.services.document_extraction import (
    process_extraction_jobs,
    prune_extraction_jobs,
    utc_now,
)
from app.storage.factory import build_storage_resolver


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process durable document text extraction jobs.",
    )
    parser.add_argument("--batch-size", type=positive_integer, default=None)
    parser.add_argument("--max-jobs", type=positive_integer, default=None)
    parser.add_argument("--document-id", type=positive_integer, default=None)
    parser.add_argument("--lease-seconds", type=positive_integer, default=None)
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Queue failed extraction records before processing.",
    )
    parser.add_argument(
        "--prune-completed",
        action="store_true",
        help="Prune terminal jobs older than the configured retention.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: Callable = SessionLocal,
    storage_config: AttachmentConfig = ATTACHMENT_CONFIG,
    extraction_config: DocumentExtractionConfig = DOCUMENT_EXTRACTION_CONFIG,
    storage_resolver=None,
    ocr_provider=None,
) -> int:
    args = build_parser().parse_args(argv)
    resolver = storage_resolver or build_storage_resolver(storage_config)
    db = session_factory()
    try:
        retried = 0
        if args.retry_failed and extraction_config.enabled:
            from app.models.document_extraction import DocumentExtractionJob

            failed_query = (
                db.query(DocumentExtractionJob)
                .filter(DocumentExtractionJob.status == "failed")
            )
            if args.document_id is not None:
                failed_query = failed_query.filter(
                    DocumentExtractionJob.document_id == args.document_id
                )
            failed_jobs = (
                failed_query.order_by(DocumentExtractionJob.id.asc())
                .limit(args.max_jobs or extraction_config.batch_size)
                .all()
            )
            now = utc_now()
            for job in failed_jobs:
                job.status = "pending"
                job.attempt_count = 0
                job.available_at = now
                job.started_at = None
                job.lease_expires_at = None
                job.lease_token = None
                job.completed_at = None
                job.last_error_code = None
                job.last_error_message = None
                job.updated_at = now
                retried += 1
            db.commit()
        result = process_extraction_jobs(
            db,
            resolver,
            storage_config,
            extraction_config,
            ocr_provider=ocr_provider,
            batch_size=args.batch_size,
            max_jobs=args.max_jobs,
            document_id=args.document_id,
            lease_seconds=args.lease_seconds,
        )
        pruned = (
            prune_extraction_jobs(db, extraction_config)
            if args.prune_completed
            else 0
        )
    except Exception:
        db.rollback()
        print("Document extraction failed during database processing.")
        return 1
    finally:
        db.close()

    print(
        "Document extraction complete: "
        f"retried={retried}, claimed={result.claimed}, "
        f"completed={result.completed}, unavailable={result.unavailable}, "
        f"retryable={result.retryable}, failed={result.failed}, "
        f"cancelled={result.cancelled}, skipped={result.skipped}, "
        f"pruned={pruned}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
