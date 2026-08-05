import argparse

from app.core.config import PRECONSTRUCTION_AI_CONFIG
from app.db.database import SessionLocal
from app.preconstruction.factory import build_preconstruction_provider
from app.services.preconstruction import process_analysis_attempts, retry_failed_runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a finite batch of preconstruction analysis attempts."
    )
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--lease-seconds", type=int)
    return parser


def _positive(value: int | None, name: str) -> int | None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        batch_size = _positive(args.batch_size, "batch-size")
        max_jobs = _positive(args.max_jobs, "max-jobs")
        run_id = _positive(args.run_id, "run-id")
        lease_seconds = _positive(args.lease_seconds, "lease-seconds")
    except ValueError as error:
        print(str(error))
        return 2

    config = PRECONSTRUCTION_AI_CONFIG
    try:
        provider = build_preconstruction_provider(config)
    except RuntimeError:
        print("Preconstruction provider configuration is invalid.")
        return 1

    db = SessionLocal()
    retried = 0
    try:
        if args.retry_failed:
            retried = retry_failed_runs(
                db,
                provider,
                run_id=run_id,
                limit=max_jobs or batch_size or config.batch_size,
            )
        result = process_analysis_attempts(
            db,
            provider,
            config,
            batch_size=batch_size,
            max_jobs=max_jobs,
            run_id=run_id,
            lease_seconds=lease_seconds,
        )
    except Exception:
        db.rollback()
        print("Preconstruction analysis failed during database processing.")
        return 1
    finally:
        db.close()

    print(
        "Preconstruction analysis complete: "
        f"retried={retried}, claimed={result.claimed}, "
        f"completed={result.completed}, warnings={result.warnings}, "
        f"retryable={result.retryable}, failed={result.failed}, "
        f"unavailable={result.unavailable}, cancelled={result.cancelled}, "
        f"skipped={result.skipped}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
