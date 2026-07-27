import argparse
from collections.abc import Callable, Sequence

from app.core.config import ATTACHMENT_CONFIG, AttachmentConfig
from app.db.database import SessionLocal
from app.services.attachment_cleanup import (
    process_cleanup_jobs,
    prune_completed_cleanup_jobs,
)
from app.storage.attachment import AttachmentStorageError
from app.storage.factory import build_storage_resolver


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be greater than zero"
        )
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process durable attachment object cleanup jobs.",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=None,
    )
    parser.add_argument(
        "--max-jobs",
        type=positive_integer,
        default=None,
    )
    parser.add_argument(
        "--prune-completed",
        action="store_true",
        help="Prune completed jobs older than the configured retention.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: Callable = SessionLocal,
    config: AttachmentConfig = ATTACHMENT_CONFIG,
    storage_resolver=None,
) -> int:
    args = build_parser().parse_args(argv)
    resolver = storage_resolver or build_storage_resolver(config)

    try:
        resolver(config.storage_provider)
    except AttachmentStorageError as error:
        print(
            "Attachment cleanup setup failed: "
            f"{error.category} storage configuration error."
        )
        return 1

    db = session_factory()
    try:
        result = process_cleanup_jobs(
            db,
            resolver,
            config,
            batch_size=args.batch_size,
            max_jobs=args.max_jobs,
        )
        pruned = (
            prune_completed_cleanup_jobs(db, config)
            if args.prune_completed
            else 0
        )
    except Exception:
        db.rollback()
        print("Attachment cleanup failed during database processing.")
        return 1
    finally:
        db.close()

    print(
        "Attachment cleanup complete: "
        f"claimed={result.claimed}, "
        f"completed={result.completed}, "
        f"retryable={result.retryable}, "
        f"failed={result.failed}, "
        f"pruned={pruned}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
