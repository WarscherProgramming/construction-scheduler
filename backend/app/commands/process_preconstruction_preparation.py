import argparse

from app.core.config import PRECONSTRUCTION_PREPARATION_CONFIG
from app.db.database import SessionLocal
from app.services.preconstruction_content import process_preparation_runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a finite batch of preconstruction source preparation runs."
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

    db = SessionLocal()
    try:
        if args.retry_failed:
            from app.models.preconstruction import PreconstructionPreparationRun
            from app.services.preconstruction_content import retry_preparation_run

            query = db.query(PreconstructionPreparationRun).filter(
                PreconstructionPreparationRun.status == "failed",
                PreconstructionPreparationRun.attempt_count
                < PreconstructionPreparationRun.max_attempts,
            )
            if run_id is not None:
                query = query.filter(PreconstructionPreparationRun.id == run_id)
            for failed in query.order_by(PreconstructionPreparationRun.id.asc()).limit(
                max_jobs or batch_size or PRECONSTRUCTION_PREPARATION_CONFIG.batch_size
            ).all():
                retry_preparation_run(db, failed)
        result = process_preparation_runs(
            db,
            PRECONSTRUCTION_PREPARATION_CONFIG,
            batch_size=batch_size,
            max_jobs=max_jobs,
            run_id=run_id,
            lease_seconds=lease_seconds,
        )
    except Exception:
        db.rollback()
        print("Preconstruction source preparation failed during database processing.")
        return 1
    finally:
        db.close()

    print(
        "Preconstruction source preparation complete: "
        f"claimed={result.claimed}, completed={result.completed}, "
        f"warnings={result.warnings}, retryable={result.retryable}, "
        f"failed={result.failed}, unavailable={result.unavailable}, "
        f"cancelled={result.cancelled}, skipped={result.skipped}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
