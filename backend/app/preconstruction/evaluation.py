"""Deterministic evaluation of the matching engine and provider validation.

A labeled golden suite in, a scored report out. Pure: no ORM, no session, no
configuration, no network, no provider, no database write, and no project data.

Every case states its expected outcome explicitly, so the report answers one
question honestly — *does the documented behaviour still hold?* — rather than
producing an opaque quality score. There is no machine learning, no embedding,
no similarity model, and no threshold tuned against real projects.

Two suites are supported:

- **deterministic** — the M18.4 matching engine scored against expected match
  classes, reason codes, and coverage outcomes.
- **provider_assisted** — a provider validation result scored against the
  deterministic candidates it was allowed to judge. It measures agreement and
  refusal behaviour; it never measures whether the provider was "right", which
  only a human reviewer can decide.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
import json

from app.preconstruction.comparison import (
    FINDING_TYPES,
    MATCH_CLASSES,
    MATCH_CLASS_ORDER,
)
from app.preconstruction.matching import (
    ComparableAssertion,
    compare_assertions,
    generate_coverage_candidates,
)


EVALUATION_SUITE_VERSION = "preconstruction-evaluation-1"

EVALUATION_SUITES = {
    "deterministic": "Deterministic matching engine",
    "provider_assisted": "Provider validation behaviour",
}

# Every way a case can fail, named so a regression report is actionable rather
# than a bare count.
EVALUATION_OUTCOMES = {
    "passed": "Expected behaviour held",
    "wrong_match_class": "Match class differed from the expectation",
    "missing_reason": "An expected reason code was absent",
    "unexpected_reason": "A forbidden reason code was present",
    "wrong_finding_type": "Coverage outcome differed from the expectation",
    "missing_candidate": "An expected candidate was not produced",
    "unexpected_candidate": "An unexpected candidate was produced",
    "wrong_disposition": "Provider disposition differed from the expectation",
}


def _assertion(
    assertion_id: int,
    *,
    concept_code: str,
    subject: str,
    document_role: str,
    assertion_type: str = "physical_item",
    inclusion_state: str = "included",
    requirement: str = "",
    responsibility_party: str | None = None,
    discipline: str | None = None,
    trade: str | None = None,
    specification_section: str | None = None,
    drawing_sheet: str | None = None,
    quantity_value: Decimal | None = None,
    quantity_unit: str | None = None,
    location_text: str | None = None,
) -> ComparableAssertion:
    """Build one fixture assertion. Fixture data only; never project data."""
    return ComparableAssertion(
        assertion_id=assertion_id,
        review_id=assertion_id,
        source_id=assertion_id,
        document_role=document_role,
        concept_code=concept_code,
        assertion_type=assertion_type,
        inclusion_state=inclusion_state,
        subject=subject,
        normalized_subject=" ".join(subject.casefold().split()),
        normalized_requirement=" ".join(requirement.casefold().split()),
        responsibility_party=responsibility_party,
        discipline=discipline,
        trade=trade,
        specification_section=specification_section,
        drawing_sheet=drawing_sheet,
        quantity_value=quantity_value,
        quantity_unit=quantity_unit,
        location_text=location_text,
        origin="provider",
        content_hash="",
        evidence_ids=(assertion_id,),
    )


@dataclass(frozen=True)
class MatchCase:
    """One labeled requirement/coverage pair with its expected classification."""

    name: str
    requirement: ComparableAssertion
    coverage: ComparableAssertion
    expected_match_class: str
    expected_reasons: tuple[str, ...] = ()
    forbidden_reasons: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class CoverageCase:
    """One labeled population with its expected coverage finding types."""

    name: str
    requirements: tuple[ComparableAssertion, ...]
    coverages: tuple[ComparableAssertion, ...]
    expected_finding_types: tuple[str, ...]
    note: str = ""


@dataclass
class CaseResult:
    name: str
    outcome: str
    expected: str
    observed: str

    def payload(self) -> dict:
        return {
            "name": self.name,
            "outcome": self.outcome,
            "expected": self.expected,
            "observed": self.observed,
        }


@dataclass
class EvaluationReport:
    suite: str
    suite_version: str
    total: int = 0
    passed: int = 0
    failures: list[CaseResult] = field(default_factory=list)
    outcome_counts: dict[str, int] = field(default_factory=dict)

    def record(self, result: CaseResult) -> None:
        self.total += 1
        self.outcome_counts[result.outcome] = (
            self.outcome_counts.get(result.outcome, 0) + 1
        )
        if result.outcome == "passed":
            self.passed += 1
        else:
            self.failures.append(result)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    def digest(self) -> str:
        """Stable hash over the scored outcomes.

        Identical engine behaviour reproduces the digest exactly, so a change
        is visible without diffing a full report.
        """
        payload = {
            "suite": self.suite,
            "suite_version": self.suite_version,
            "total": self.total,
            "passed": self.passed,
            "outcomes": dict(sorted(self.outcome_counts.items())),
            "failures": [item.payload() for item in self.failures],
        }
        serialized = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return sha256(serialized.encode("utf-8")).hexdigest()

    def payload(self) -> dict:
        return {
            "suite": self.suite,
            "suite_label": EVALUATION_SUITES[self.suite],
            "suite_version": self.suite_version,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "outcome_counts": dict(sorted(self.outcome_counts.items())),
            "failures": [item.payload() for item in self.failures],
            "digest": self.digest(),
        }


# --- the deterministic golden suite -----------------------------------------
#
# Each case pins one documented rule from AI_SCOPE_COMPARISON.md. A change in
# engine behaviour that is not also a documentation change fails here.

MATCH_CASES: tuple[MatchCase, ...] = (
    MatchCase(
        "identical_concept_and_subject_is_exact",
        _assertion(
            1,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="specification",
            specification_section="26 51 00",
            discipline="Electrical",
            trade="Electrical",
        ),
        _assertion(
            2,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="proposal",
            specification_section="26 51 00",
            discipline="Electrical",
            trade="Electrical",
        ),
        "exact",
        expected_reasons=("concept_match", "subject_exact"),
    ),
    MatchCase(
        "lexical_overlap_without_concept_match_is_capped_at_weak",
        _assertion(
            3,
            concept_code="electrical.lighting_fixture",
            subject="Recessed lighting fixtures in corridor",
            document_role="specification",
            specification_section="26 51 00",
            discipline="Electrical",
            trade="Electrical",
        ),
        _assertion(
            4,
            concept_code="hvac.air_handling_unit",
            subject="Recessed lighting fixtures in corridor",
            document_role="proposal",
            specification_section="26 51 00",
            discipline="Electrical",
            trade="Electrical",
        ),
        "weak",
        forbidden_reasons=("concept_match",),
        note="Lexical overlap alone never implies coverage.",
    ),
    MatchCase(
        "responsibility_mismatch_caps_the_class_at_strong",
        _assertion(
            5,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="specification",
            responsibility_party="Electrical Contractor",
        ),
        _assertion(
            6,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="proposal",
            responsibility_party="Owner",
        ),
        "strong",
        expected_reasons=("concept_match", "responsibility_mismatch"),
        note="An exact-looking score never hides a contradiction.",
    ),
    MatchCase(
        "quantity_mismatch_is_reported_as_a_material_conflict",
        _assertion(
            7,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="specification",
            quantity_value=Decimal("120"),
            quantity_unit="each",
        ),
        _assertion(
            8,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="proposal",
            quantity_value=Decimal("80"),
            quantity_unit="each",
        ),
        "strong",
        expected_reasons=("concept_match", "quantity_mismatch"),
    ),
    MatchCase(
        "unit_mismatch_is_distinct_from_quantity_mismatch",
        _assertion(
            9,
            concept_code="concrete.concrete_slab",
            subject="Slab on grade",
            document_role="specification",
            quantity_value=Decimal("100"),
            quantity_unit="square_foot",
        ),
        _assertion(
            10,
            concept_code="concrete.concrete_slab",
            subject="Slab on grade",
            document_role="proposal",
            quantity_value=Decimal("100"),
            quantity_unit="cubic_yard",
        ),
        "strong",
        expected_reasons=("concept_match", "unit_mismatch"),
        forbidden_reasons=("quantity_match",),
    ),
    MatchCase(
        "unrelated_scope_produces_no_match",
        _assertion(
            11,
            concept_code="electrical.lighting_fixture",
            subject="LED lighting fixtures",
            document_role="specification",
        ),
        _assertion(
            12,
            concept_code="sitework.earthwork",
            subject="Site earthwork and grading",
            document_role="proposal",
            assertion_type="activity",
        ),
        "none",
        forbidden_reasons=("concept_match", "subject_exact"),
    ),
)


COVERAGE_CASES: tuple[CoverageCase, ...] = (
    CoverageCase(
        "covered_requirement_produces_no_gap",
        (
            _assertion(
                20,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="specification",
                specification_section="26 51 00",
                discipline="Electrical",
                trade="Electrical",
            ),
        ),
        (
            _assertion(
                21,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="proposal",
                specification_section="26 51 00",
                discipline="Electrical",
                trade="Electrical",
            ),
        ),
        (),
    ),
    CoverageCase(
        "uncovered_requirement_is_missing_coverage",
        (
            _assertion(
                22,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="specification",
            ),
        ),
        (
            _assertion(
                23,
                concept_code="sitework.earthwork",
                subject="Site earthwork and grading",
                document_role="proposal",
                assertion_type="activity",
            ),
        ),
        ("missing_coverage",),
    ),
    CoverageCase(
        "excluded_requirement_is_never_a_coverage_gap",
        (
            _assertion(
                24,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="specification",
                inclusion_state="excluded",
            ),
        ),
        (),
        (),
        note="A requirement that excludes itself is not a gap.",
    ),
    CoverageCase(
        "responsibility_conflict_is_reported_on_a_covered_requirement",
        (
            _assertion(
                25,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="specification",
                specification_section="26 51 00",
                discipline="Electrical",
                trade="Electrical",
                responsibility_party="Electrical Contractor",
            ),
        ),
        (
            _assertion(
                26,
                concept_code="electrical.lighting_fixture",
                subject="LED lighting fixtures",
                document_role="proposal",
                specification_section="26 51 00",
                discipline="Electrical",
                trade="Electrical",
                responsibility_party="Owner",
            ),
        ),
        ("responsibility_conflict",),
    ),
)


def evaluate_matching(
    match_cases: tuple[MatchCase, ...] = MATCH_CASES,
    coverage_cases: tuple[CoverageCase, ...] = COVERAGE_CASES,
    *,
    covered_minimum: str = "strong",
    maximum_candidates: int = 500,
) -> EvaluationReport:
    """Score the deterministic engine against the labeled golden suite."""
    report = EvaluationReport(
        suite="deterministic", suite_version=EVALUATION_SUITE_VERSION
    )

    for case in match_cases:
        result = compare_assertions(case.requirement, case.coverage)
        if result.match_class != case.expected_match_class:
            report.record(
                CaseResult(
                    case.name,
                    "wrong_match_class",
                    case.expected_match_class,
                    result.match_class,
                )
            )
            continue
        missing = [
            reason for reason in case.expected_reasons if reason not in result.reasons
        ]
        if missing:
            report.record(
                CaseResult(
                    case.name,
                    "missing_reason",
                    ",".join(sorted(missing)),
                    ",".join(sorted(result.reasons)),
                )
            )
            continue
        present = [
            reason for reason in case.forbidden_reasons if reason in result.reasons
        ]
        if present:
            report.record(
                CaseResult(
                    case.name,
                    "unexpected_reason",
                    "",
                    ",".join(sorted(present)),
                )
            )
            continue
        report.record(
            CaseResult(case.name, "passed", case.expected_match_class, result.match_class)
        )

    for case in coverage_cases:
        candidates, _warnings = generate_coverage_candidates(
            list(case.requirements),
            list(case.coverages),
            covered_minimum=covered_minimum,
            maximum_candidates=maximum_candidates,
        )
        observed = tuple(sorted(item.finding_type for item in candidates))
        expected = tuple(sorted(case.expected_finding_types))
        if observed == expected:
            report.record(
                CaseResult(case.name, "passed", ",".join(expected), ",".join(observed))
            )
        elif len(observed) < len(expected):
            report.record(
                CaseResult(
                    case.name, "missing_candidate", ",".join(expected), ",".join(observed)
                )
            )
        elif len(observed) > len(expected):
            report.record(
                CaseResult(
                    case.name,
                    "unexpected_candidate",
                    ",".join(expected),
                    ",".join(observed),
                )
            )
        else:
            report.record(
                CaseResult(
                    case.name,
                    "wrong_finding_type",
                    ",".join(expected),
                    ",".join(observed),
                )
            )

    return report


@dataclass(frozen=True)
class DispositionCase:
    """One provider disposition scored against what it was allowed to do."""

    candidate_key: str
    expected_disposition: str
    observed_disposition: str
    observed_finding_type: str | None = None
    allowed_finding_types: tuple[str, ...] = ()


def evaluate_provider_dispositions(
    cases: tuple[DispositionCase, ...],
) -> EvaluationReport:
    """Score provider validation behaviour against the deterministic baseline.

    This measures agreement and refusal, never correctness: whether a finding
    is genuinely a gap is a human decision, and no evaluation number here can
    accept, reject, or escalate anything.
    """
    report = EvaluationReport(
        suite="provider_assisted", suite_version=EVALUATION_SUITE_VERSION
    )
    for case in cases:
        if (
            case.observed_finding_type is not None
            and case.allowed_finding_types
            and case.observed_finding_type not in case.allowed_finding_types
        ):
            report.record(
                CaseResult(
                    case.candidate_key,
                    "wrong_finding_type",
                    ",".join(sorted(case.allowed_finding_types)),
                    case.observed_finding_type,
                )
            )
            continue
        if case.observed_disposition != case.expected_disposition:
            report.record(
                CaseResult(
                    case.candidate_key,
                    "wrong_disposition",
                    case.expected_disposition,
                    case.observed_disposition,
                )
            )
            continue
        report.record(
            CaseResult(
                case.candidate_key,
                "passed",
                case.expected_disposition,
                case.observed_disposition,
            )
        )
    return report


# --- import-time validation -------------------------------------------------

_CASE_NAMES = [case.name for case in MATCH_CASES] + [
    case.name for case in COVERAGE_CASES
]
if len(set(_CASE_NAMES)) != len(_CASE_NAMES):
    raise RuntimeError("Duplicate evaluation case name")
for _case in MATCH_CASES:
    if _case.expected_match_class not in MATCH_CLASSES:
        raise RuntimeError(f"Unknown match class in case {_case.name}")
    if _case.expected_match_class not in MATCH_CLASS_ORDER:
        raise RuntimeError(f"Unordered match class in case {_case.name}")
for _case in COVERAGE_CASES:
    for _finding_type in _case.expected_finding_types:
        if _finding_type not in FINDING_TYPES:
            raise RuntimeError(f"Unknown finding type in case {_case.name}")
if set(EVALUATION_SUITES) != {"deterministic", "provider_assisted"}:
    raise RuntimeError("Unexpected evaluation suite set")
