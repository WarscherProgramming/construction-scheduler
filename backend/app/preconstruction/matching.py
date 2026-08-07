"""Deterministic cross-document scope matching.

Pure module: frozen dataclasses in, candidates out. No ORM, no session, no
configuration, no network, no provider. Every decision is reproducible from
the inputs and is accompanied by explicit reason codes.

There are no embeddings, no semantic similarity, no machine learning, and no
undocumented keyword heuristics. The only lexical signal is bounded token
overlap (Jaccard on normalized tokens), which can never on its own raise a
candidate above the ``weak`` match class because a taxonomy concept match is
required for anything higher.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import unicodedata

from app.preconstruction.comparison import (
    MATCH_SCORE_MAXIMUM,
    MATCH_WEIGHTS,
    MATERIAL_MISMATCH_REASONS,
    classify_match,
    match_class_at_least,
)


# Tokens shorter than this carry no discriminating value and are dropped so
# that "a", "of", and stray punctuation do not inflate overlap.
MINIMUM_TOKEN_LENGTH = 2
SUBJECT_OVERLAP_FLOOR = 0.34
REQUIREMENT_OVERLAP_FLOOR = 0.25

# Assertion types that can sensibly satisfy one another across sides.
COMPATIBLE_ASSERTION_TYPES = {
    "requirement": {"requirement", "physical_item", "system", "activity", "deliverable"},
    "physical_item": {"physical_item", "requirement", "system", "procurement_requirement"},
    "system": {"system", "physical_item", "requirement"},
    "activity": {"activity", "requirement", "coordination_requirement"},
    "responsibility": {"responsibility", "requirement"},
    "deliverable": {"deliverable", "requirement", "informational"},
    "testing_requirement": {"testing_requirement", "requirement", "activity"},
    "coordination_requirement": {"coordination_requirement", "requirement", "activity"},
    "procurement_requirement": {"procurement_requirement", "physical_item", "requirement"},
    "allowance": {"allowance", "requirement"},
    "alternate": {"alternate", "requirement"},
    "exclusion": {"exclusion"},
    "informational": {"informational", "deliverable"},
}

EXCLUDING_INCLUSION_STATES = ("excluded", "not_applicable")


@dataclass(frozen=True)
class ComparableAssertion:
    """A read-only projection of one accepted M18.3 assertion."""

    assertion_id: int
    review_id: int | None
    source_id: int
    document_role: str
    concept_code: str
    assertion_type: str
    inclusion_state: str
    subject: str
    normalized_subject: str
    normalized_requirement: str
    responsibility_party: str | None
    discipline: str | None
    trade: str | None
    specification_section: str | None
    drawing_sheet: str | None
    quantity_value: Decimal | None
    quantity_unit: str | None
    location_text: str | None
    origin: str
    content_hash: str
    evidence_ids: tuple[int, ...] = ()
    drawing_revision_id: int | None = None
    revision_code: str | None = None
    revision_ordinal: int | None = None


@dataclass(frozen=True)
class MatchResult:
    match_class: str
    score: int
    reasons: tuple[str, ...]

    def has_material_conflict(self) -> bool:
        return any(reason in MATERIAL_MISMATCH_REASONS for reason in self.reasons)


@dataclass(frozen=True)
class Candidate:
    """One deterministic comparison candidate, before any provider input."""

    candidate_key: str
    finding_type: str
    requirement_assertion_ids: tuple[int, ...]
    coverage_assertion_ids: tuple[int, ...]
    match_class: str
    match_score: int
    match_reasons: tuple[str, ...]
    title: str
    summary: str
    rationale: str
    side_by_assertion: dict[int, str] = field(default_factory=dict)
    role_by_assertion: dict[int, str] = field(default_factory=dict)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def tokenize(value: str | None) -> frozenset[str]:
    """Deterministic token set: NFKC, case-folded, punctuation-split."""
    normalized = _normalize(value)
    if not normalized:
        return frozenset()
    tokens = []
    current = []
    for character in normalized:
        if character.isalnum():
            current.append(character)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return frozenset(
        token for token in tokens if len(token) >= MINIMUM_TOKEN_LENGTH
    )


def overlap_ratio(left: frozenset[str], right: frozenset[str]) -> float:
    """Jaccard overlap. Deterministic, bounded, dependency-free."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _quantity_reason(
    left: ComparableAssertion, right: ComparableAssertion
) -> str | None:
    if left.quantity_value is None or right.quantity_value is None:
        return None
    if left.quantity_unit != right.quantity_unit:
        return "unit_mismatch"
    return (
        "quantity_match"
        if left.quantity_value == right.quantity_value
        else "quantity_mismatch"
    )


def compare_assertions(
    requirement: ComparableAssertion, coverage: ComparableAssertion
) -> MatchResult:
    """Score one requirement/coverage pair and explain every component."""
    reasons: list[str] = []
    score = 0

    if requirement.concept_code == coverage.concept_code:
        reasons.append("concept_match")
        score += MATCH_WEIGHTS["concept_match"]

    compatible = COMPATIBLE_ASSERTION_TYPES.get(requirement.assertion_type, set())
    if coverage.assertion_type in compatible:
        reasons.append("assertion_type_compatible")
        score += MATCH_WEIGHTS["assertion_type_compatible"]

    if (
        requirement.normalized_subject
        and requirement.normalized_subject == coverage.normalized_subject
    ):
        reasons.append("subject_exact")
        score += MATCH_WEIGHTS["subject_exact"]
    else:
        ratio = overlap_ratio(
            tokenize(requirement.normalized_subject),
            tokenize(coverage.normalized_subject),
        )
        if ratio >= SUBJECT_OVERLAP_FLOOR:
            reasons.append("subject_overlap")
            score += round(MATCH_WEIGHTS["subject_overlap"] * ratio)

    requirement_ratio = overlap_ratio(
        tokenize(requirement.normalized_requirement),
        tokenize(coverage.normalized_requirement),
    )
    if requirement_ratio >= REQUIREMENT_OVERLAP_FLOOR:
        reasons.append("requirement_overlap")
        score += round(MATCH_WEIGHTS["requirement_overlap"] * requirement_ratio)

    if (
        requirement.specification_section
        and _normalize(requirement.specification_section)
        == _normalize(coverage.specification_section)
    ):
        reasons.append("specification_section_match")
        score += MATCH_WEIGHTS["specification_section_match"]

    if (
        requirement.drawing_sheet
        and _normalize(requirement.drawing_sheet) == _normalize(coverage.drawing_sheet)
    ):
        reasons.append("drawing_sheet_match")
        score += MATCH_WEIGHTS["drawing_sheet_match"]

    if requirement.responsibility_party and coverage.responsibility_party:
        if _normalize(requirement.responsibility_party) == _normalize(
            coverage.responsibility_party
        ):
            reasons.append("responsibility_match")
            score += MATCH_WEIGHTS["responsibility_match"]
        else:
            reasons.append("responsibility_mismatch")

    if requirement.discipline and _normalize(requirement.discipline) == _normalize(
        coverage.discipline
    ):
        reasons.append("discipline_match")
        score += MATCH_WEIGHTS["discipline_match"]

    if requirement.trade and _normalize(requirement.trade) == _normalize(coverage.trade):
        reasons.append("trade_match")
        score += MATCH_WEIGHTS["trade_match"]

    quantity_reason = _quantity_reason(requirement, coverage)
    if quantity_reason:
        reasons.append(quantity_reason)
        if quantity_reason == "quantity_match":
            score += MATCH_WEIGHTS["quantity_match"]

    if requirement.location_text and coverage.location_text:
        if _normalize(requirement.location_text) == _normalize(coverage.location_text):
            reasons.append("location_match")
        else:
            reasons.append("location_mismatch")

    if coverage.inclusion_state == "excluded" and requirement.inclusion_state == "included":
        reasons.append("inclusion_conflict")
    elif coverage.inclusion_state == "conditional":
        reasons.append("conditional_inclusion")

    score = min(score, MATCH_SCORE_MAXIMUM)
    ordered = tuple(sorted(set(reasons)))
    return MatchResult(classify_match(score, ordered), score, ordered)


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"


def _candidate_key(finding_type: str, requirement_ids, coverage_ids) -> str:
    left = ",".join(str(item) for item in sorted(requirement_ids))
    right = ",".join(str(item) for item in sorted(coverage_ids))
    return f"{finding_type}:{left}|{right}"


def _coverage_candidate(
    requirement: ComparableAssertion,
    best: tuple[ComparableAssertion, MatchResult] | None,
    covered_minimum: str,
) -> Candidate | None:
    """Turn one requirement's best coverage match into a candidate, if any.

    Wording is deliberately hedged: these are potential issues for a human to
    judge, never confirmed omissions or contract conclusions.

    A ``weak`` best match is treated as missing coverage rather than partial
    coverage. Weak matches carry no taxonomy concept match, so lexical overlap
    alone must never be presented as partial coverage; the near miss is still
    linked so the reviewer can see what was considered.
    """
    if best is None or best[1].match_class == "weak":
        near_miss = best[0] if best else None
        near_result = best[1] if best else None
        sides = {requirement.assertion_id: "requirement"}
        roles = {requirement.assertion_id: "primary"}
        coverage_ids: tuple[int, ...] = ()
        if near_miss is not None:
            sides[near_miss.assertion_id] = "coverage"
            roles[near_miss.assertion_id] = "near_match"
            coverage_ids = (near_miss.assertion_id,)
        return Candidate(
            candidate_key=_candidate_key(
                "missing_coverage", (requirement.assertion_id,), coverage_ids
            ),
            finding_type="missing_coverage",
            requirement_assertion_ids=(requirement.assertion_id,),
            coverage_assertion_ids=coverage_ids,
            match_class=near_result.match_class if near_result else "none",
            match_score=near_result.score if near_result else 0,
            match_reasons=near_result.reasons if near_result else (),
            title=_truncate(f"Potential missing coverage: {requirement.subject}", 200),
            summary=_truncate(
                "No accepted coverage assertion appears to match the requirement "
                f"\"{requirement.subject}\"."
                + (
                    f" Closest near match: \"{near_miss.subject}\"."
                    if near_miss is not None
                    else ""
                ),
                600,
            ),
            rationale=(
                "Deterministic comparison found no coverage-side assertion "
                "sharing this taxonomy concept above the configured match "
                "threshold. This may indicate uncovered scope and requires "
                "human review."
            ),
            side_by_assertion=sides,
            role_by_assertion=roles,
        )

    coverage, result = best
    if match_class_at_least(result.match_class, covered_minimum):
        # Covered well enough; only material contradictions are reported.
        if "inclusion_conflict" in result.reasons:
            finding_type = "explicit_exclusion"
        elif "responsibility_mismatch" in result.reasons:
            finding_type = "responsibility_conflict"
        elif "quantity_mismatch" in result.reasons or "unit_mismatch" in result.reasons:
            finding_type = "quantity_mismatch"
        elif "location_mismatch" in result.reasons:
            finding_type = "location_mismatch"
        elif "conditional_inclusion" in result.reasons:
            finding_type = "conditional_scope"
        else:
            return None
    else:
        finding_type = "partial_coverage"

    titles = {
        "explicit_exclusion": "Potential explicit exclusion",
        "responsibility_conflict": "Potential responsibility conflict",
        "quantity_mismatch": "Potential quantity mismatch",
        "location_mismatch": "Potential location mismatch",
        "conditional_scope": "Potential conditional scope",
        "partial_coverage": "Potential partial coverage",
    }
    summaries = {
        "explicit_exclusion": (
            "The requirement appears included while the matching coverage "
            "assertion appears excluded."
        ),
        "responsibility_conflict": (
            "The requirement and the matching coverage assertion appear to "
            "assign different responsible parties."
        ),
        "quantity_mismatch": (
            "The requirement and the matching coverage assertion appear to "
            "state different quantities or units."
        ),
        "location_mismatch": (
            "The requirement and the matching coverage assertion appear to "
            "state different locations."
        ),
        "conditional_scope": (
            "Coverage for this requirement appears conditional."
        ),
        "partial_coverage": (
            "Coverage for this requirement appears incomplete; the closest "
            "coverage assertion matched only partially."
        ),
    }
    return Candidate(
        candidate_key=_candidate_key(
            finding_type, (requirement.assertion_id,), (coverage.assertion_id,)
        ),
        finding_type=finding_type,
        requirement_assertion_ids=(requirement.assertion_id,),
        coverage_assertion_ids=(coverage.assertion_id,),
        match_class=result.match_class,
        match_score=result.score,
        match_reasons=result.reasons,
        title=_truncate(f"{titles[finding_type]}: {requirement.subject}", 200),
        summary=_truncate(
            f"{summaries[finding_type]} Requirement: \"{requirement.subject}\". "
            f"Coverage: \"{coverage.subject}\".",
            600,
        ),
        rationale=_truncate(
            "Deterministic match class "
            f"{result.match_class} (score {result.score}). Reasons: "
            + ", ".join(result.reasons or ("no matching components",))
            + ". Requires human review.",
            2000,
        ),
        side_by_assertion={
            requirement.assertion_id: "requirement",
            coverage.assertion_id: "coverage",
        },
        role_by_assertion={
            requirement.assertion_id: "primary",
            coverage.assertion_id: (
                "contradictory"
                if finding_type
                in ("explicit_exclusion", "responsibility_conflict", "quantity_mismatch",
                    "location_mismatch")
                else "near_match"
            ),
        },
    )


def generate_coverage_candidates(
    requirements: list[ComparableAssertion],
    coverages: list[ComparableAssertion],
    *,
    covered_minimum: str = "strong",
    maximum_candidates: int,
) -> tuple[list[Candidate], list[str]]:
    """Deterministic requirement-versus-coverage candidate generation.

    Ordering is stable: requirements are processed by assertion id, and the
    best coverage match is resolved by (score, assertion id) so ties never
    depend on input order.
    """
    candidates: list[Candidate] = []
    warnings: list[str] = []
    for requirement in sorted(requirements, key=lambda item: item.assertion_id):
        if requirement.inclusion_state in EXCLUDING_INCLUSION_STATES:
            # A requirement that is itself excluded or not applicable is not a
            # coverage gap.
            continue
        scored = [
            (coverage, compare_assertions(requirement, coverage))
            for coverage in coverages
        ]
        scored = [item for item in scored if item[1].match_class != "none"]
        best = None
        if scored:
            best = max(
                scored,
                key=lambda item: (item[1].score, -item[0].assertion_id),
            )
        candidate = _coverage_candidate(requirement, best, covered_minimum)
        if candidate is None:
            continue
        candidates.append(candidate)
        if len(candidates) >= maximum_candidates:
            warnings.append("candidate_limit_reached")
            break
    return candidates, warnings


def generate_revision_candidates(
    prior: list[ComparableAssertion],
    current: list[ComparableAssertion],
    *,
    maximum_candidates: int,
) -> tuple[list[Candidate], list[str]]:
    """Compare assertions across revisions of the same drawing sheet.

    This is structured assertion comparison over revision lineage. It performs
    no visual, image, or geometric comparison of drawing content.
    """
    candidates: list[Candidate] = []
    warnings: list[str] = []

    def sheet_key(item: ComparableAssertion) -> str:
        return _normalize(item.drawing_sheet) or f"source:{item.source_id}"

    prior_by_sheet: dict[str, list[ComparableAssertion]] = {}
    for item in prior:
        prior_by_sheet.setdefault(sheet_key(item), []).append(item)
    current_by_sheet: dict[str, list[ComparableAssertion]] = {}
    for item in current:
        current_by_sheet.setdefault(sheet_key(item), []).append(item)

    shared = sorted(set(prior_by_sheet) & set(current_by_sheet))
    if not shared:
        warnings.append("revision_lineage_incomplete")

    for key in shared:
        prior_items = sorted(prior_by_sheet[key], key=lambda item: item.assertion_id)
        current_items = sorted(current_by_sheet[key], key=lambda item: item.assertion_id)
        matched_current: set[int] = set()

        for previous in prior_items:
            scored = [
                (item, compare_assertions(previous, item))
                for item in current_items
                if item.assertion_id not in matched_current
            ]
            scored = [item for item in scored if item[1].match_class != "none"]
            best = (
                max(scored, key=lambda item: (item[1].score, -item[0].assertion_id))
                if scored
                else None
            )
            if best is None:
                candidates.append(
                    Candidate(
                        candidate_key=_candidate_key(
                            "revision_removed_scope", (previous.assertion_id,), ()
                        ),
                        finding_type="revision_removed_scope",
                        requirement_assertion_ids=(previous.assertion_id,),
                        coverage_assertion_ids=(),
                        match_class="none",
                        match_score=0,
                        match_reasons=("revision_lineage",),
                        title=_truncate(
                            f"Scope appears removed by revision: {previous.subject}", 200
                        ),
                        summary=_truncate(
                            f"\"{previous.subject}\" appears in the prior revision but "
                            "has no comparable assertion in the current revision.",
                            600,
                        ),
                        rationale=(
                            "Deterministic revision comparison found no comparable "
                            "current-revision assertion for this sheet. Requires "
                            "human review."
                        ),
                        side_by_assertion={previous.assertion_id: "prior_revision"},
                        role_by_assertion={previous.assertion_id: "primary"},
                    )
                )
                continue

            item, result = best
            matched_current.add(item.assertion_id)
            if result.match_class == "exact" and not result.has_material_conflict():
                continue
            candidates.append(
                Candidate(
                    candidate_key=_candidate_key(
                        "revision_changed_scope",
                        (previous.assertion_id,),
                        (item.assertion_id,),
                    ),
                    finding_type="revision_changed_scope",
                    requirement_assertion_ids=(previous.assertion_id,),
                    coverage_assertion_ids=(item.assertion_id,),
                    match_class=result.match_class,
                    match_score=result.score,
                    match_reasons=result.reasons,
                    title=_truncate(
                        f"Scope appears changed by revision: {previous.subject}", 200
                    ),
                    summary=_truncate(
                        f"\"{previous.subject}\" appears to differ between revisions. "
                        f"Current revision: \"{item.subject}\".",
                        600,
                    ),
                    rationale=_truncate(
                        f"Deterministic match class {result.match_class} "
                        f"(score {result.score}). Reasons: "
                        + ", ".join(result.reasons or ("no matching components",))
                        + ". Requires human review.",
                        2000,
                    ),
                    side_by_assertion={
                        previous.assertion_id: "prior_revision",
                        item.assertion_id: "current_revision",
                    },
                    role_by_assertion={
                        previous.assertion_id: "primary",
                        item.assertion_id: "near_match",
                    },
                )
            )
            if len(candidates) >= maximum_candidates:
                warnings.append("candidate_limit_reached")
                return candidates, warnings

        for item in current_items:
            if item.assertion_id in matched_current:
                continue
            candidates.append(
                Candidate(
                    candidate_key=_candidate_key(
                        "revision_added_scope", (), (item.assertion_id,)
                    ),
                    finding_type="revision_added_scope",
                    requirement_assertion_ids=(),
                    coverage_assertion_ids=(item.assertion_id,),
                    match_class="none",
                    match_score=0,
                    match_reasons=("revision_lineage",),
                    title=_truncate(
                        f"Scope appears added by revision: {item.subject}", 200
                    ),
                    summary=_truncate(
                        f"\"{item.subject}\" appears in the current revision but has "
                        "no comparable assertion in the prior revision.",
                        600,
                    ),
                    rationale=(
                        "Deterministic revision comparison found no comparable "
                        "prior-revision assertion for this sheet. Requires human "
                        "review."
                    ),
                    side_by_assertion={item.assertion_id: "current_revision"},
                    role_by_assertion={item.assertion_id: "primary"},
                )
            )
            if len(candidates) >= maximum_candidates:
                warnings.append("candidate_limit_reached")
                return candidates, warnings

    return candidates, warnings
