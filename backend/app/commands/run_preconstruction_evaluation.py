"""Finite evaluation of the deterministic preconstruction analysis.

Runs the labeled golden suite and prints a bounded report. It opens no
database session, reads no project data, calls no provider, performs no
network access, and writes nothing. It exits non-zero when a documented
behaviour has regressed, so it is safe to wire into a release check.

    python -m app.commands.run_preconstruction_evaluation
    python -m app.commands.run_preconstruction_evaluation --json
    python -m app.commands.run_preconstruction_evaluation --covered-minimum partial
"""

import argparse
import json

from app.preconstruction.evaluation import (
    EVALUATION_SUITE_VERSION,
    evaluate_matching,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score the deterministic matching engine against its golden suite."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the machine-readable report instead of the text summary.",
    )
    parser.add_argument(
        "--covered-minimum",
        choices=("exact", "strong", "partial"),
        default="strong",
        help="Match class a coverage assertion must reach to count as covered.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate_matching(covered_minimum=args.covered_minimum)
    payload = report.payload()

    if args.as_json:
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(
            f"Preconstruction evaluation ({EVALUATION_SUITE_VERSION}): "
            f"suite={payload['suite']} total={payload['total']} "
            f"passed={payload['passed']} failed={payload['failed']} "
            f"covered_minimum={args.covered_minimum} digest={payload['digest'][:12]}"
        )
        for failure in payload["failures"]:
            print(
                f"  FAIL {failure['name']}: {failure['outcome']} "
                f"expected={failure['expected']!r} observed={failure['observed']!r}"
            )
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
