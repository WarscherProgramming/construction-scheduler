"""Cross-document scope comparison, findings, and human review.

Comparison operates only on human-accepted M18.3 assertions. The comparison
manifest pins exact assertion ids, the exact review decision that made each
assertion eligible, and assertion content hashes, so a later review change can
never rewrite a historical finding set.

Deterministic candidate generation is the primary path and works with no AI
provider at all. Provider validation is optional, bounded, and can only keep,
reject, or escalate candidates that trusted code already produced.

Nothing here mutates an authoritative system. No RFI, Change Order, Submittal,
Task, relationship, procurement record, or notification is ever created.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from time import perf_counter

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import case, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import (
    PRECONSTRUCTION_EXECUTION_CONFIG,
    PreconstructionComparisonConfig,
    PreconstructionExecutionConfig,
)
from app.models.preconstruction import (
    PreconstructionAnalysisRun,
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)
from app.models.scope_assertion import (
    PreconstructionAssertionEvidence,
    PreconstructionAssertionReview,
    PreconstructionScopeAssertion,
    PreconstructionScopeAssertionSet,
)
from app.models.scope_comparison import (
    PreconstructionComparisonPlan,
    PreconstructionFinding,
    PreconstructionFindingAssertion,
    PreconstructionFindingEvidence,
    PreconstructionFindingReview,
    PreconstructionFindingSet,
)
from app.preconstruction import taxonomy
from app.preconstruction.comparison import (
    COMPARISON_TYPES,
    DEFAULT_SEVERITY_BY_FINDING_TYPE,
    DECISION_TO_FINDING_STATUS,
    FINDING_LINK_ROLES,
    FINDING_ORIGINS,
    FINDING_REVIEW_DECISIONS,
    FINDING_REVIEW_REASON_CODES,
    FINDING_SEVERITIES,
    FINDING_SIDES,
    FINDING_STATUSES,
    FINDING_TYPES,
    MATCH_CLASSES,
    MATCH_REASONS,
    SEVERITY_ORDER,
    comparison_type_payload,
    default_severity,
    finding_note_required,
    finding_transition_allowed,
    finding_type_allowed,
    normalize_provider_severity,
    resolve_comparison_type,
)
from app.preconstruction.execution import (
    ExecutionMetrics,
    PhaseTimer,
    estimate_pair_budget,
)
from app.preconstruction.matching import (
    Candidate,
    ComparableAssertion,
    generate_coverage_candidates,
    generate_revision_candidates,
)
from app.preconstruction.provider import (
    ProviderComparisonAssertion,
    ProviderComparisonCandidate,
    ProviderComparisonResult,
    ProviderError,
    ProviderRequest,
)
from app.services.preconstruction_execution import record_execution_metrics
from app.services.preconstruction_scope import (
    normalized_comparison_text,
    sanitize_text,
)


ELIGIBLE_STATUSES_BY_MINIMUM = {
    "accepted": ("accepted",),
    "accepted_or_needs_review": ("accepted", "needs_review"),
}
ACTIVE_PLAN_STATUSES = ("draft", "ready", "locked")
_FINDING_STATUS_ORDER = {
    "proposed": 0,
    "needs_review": 1,
    "accepted": 2,
    "intentional_exclusion": 3,
    "rejected": 4,
    "superseded": 5,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _unprocessable(detail) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
    )


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _canonical_hash(payload: object) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _normalized_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


# ---------------------------------------------------------------------------
# Comparison plans
# ---------------------------------------------------------------------------

def _plan_configuration(payload, comparison_type) -> dict:
    """Controlled configuration only: role allowlists and assertion-set ids.

    No arbitrary filter expression or SQL fragment is ever accepted.
    """
    left_roles = sorted(set(payload.left_role_filters or comparison_type.left_roles))
    right_roles = sorted(set(payload.right_role_filters or comparison_type.right_roles))
    invalid = [
        role
        for role in left_roles
        if role not in comparison_type.left_roles
    ] + [
        role
        for role in right_roles
        if role not in comparison_type.right_roles
    ]
    if invalid:
        raise _unprocessable(
            f"Roles not permitted for this comparison type: {sorted(set(invalid))}"
        )
    return {
        "comparison_type": comparison_type.value,
        "left_role_filters": left_roles,
        "right_role_filters": right_roles,
        "left_assertion_set_ids": sorted(set(payload.left_assertion_set_ids or [])),
        "right_assertion_set_ids": sorted(set(payload.right_assertion_set_ids or [])),
        "include_manual_assertions": bool(payload.include_manual_assertions),
        "minimum_review_state": payload.minimum_review_state,
        "taxonomy_version": taxonomy.TAXONOMY_VERSION,
    }


def get_comparison_plan(
    db: Session, project_id: int, plan_id: int
) -> PreconstructionComparisonPlan:
    plan = (
        db.query(PreconstructionComparisonPlan)
        .filter(
            PreconstructionComparisonPlan.id == plan_id,
            PreconstructionComparisonPlan.project_id == project_id,
        )
        .first()
    )
    if plan is None:
        raise _not_found("Comparison plan not found")
    return plan


def _require_editable_plan(plan: PreconstructionComparisonPlan) -> None:
    if plan.status == "archived":
        raise _conflict("Archived comparison plans are read-only")
    if plan.status == "locked":
        raise _conflict("Comparison plans are locked after their first run")


def _require_active_plan(plan: PreconstructionComparisonPlan) -> None:
    if plan.status == "archived":
        raise _conflict("Archived comparison plans are read-only")


def _validate_assertion_sets(
    db: Session, review_set: PreconstructionReviewSet, ids: list[int]
) -> None:
    if not ids:
        return
    found = {
        row[0]
        for row in db.query(PreconstructionScopeAssertionSet.id)
        .filter(
            PreconstructionScopeAssertionSet.project_id == review_set.project_id,
            PreconstructionScopeAssertionSet.review_set_id == review_set.id,
            PreconstructionScopeAssertionSet.id.in_(ids),
        )
        .all()
    }
    missing = sorted(set(ids) - found)
    if missing:
        raise _unprocessable(
            f"Assertion sets do not belong to this review set: {missing}"
        )


def create_comparison_plan(
    db: Session,
    review_set: PreconstructionReviewSet,
    user_id: int,
    payload,
    config: PreconstructionComparisonConfig,
) -> PreconstructionComparisonPlan:
    if review_set.status == "archived":
        raise _conflict("Archived preconstruction review sets are read-only")
    comparison_type = resolve_comparison_type(payload.comparison_type)
    if comparison_type is None:
        raise _unprocessable("Unknown comparison type")

    existing = (
        db.query(func.count(PreconstructionComparisonPlan.id))
        .filter(PreconstructionComparisonPlan.review_set_id == review_set.id)
        .scalar()
    )
    if existing >= config.max_comparison_plans_per_review_set:
        raise _conflict("Comparison plan limit reached for this review set")

    _validate_assertion_sets(db, review_set, payload.left_assertion_set_ids or [])
    _validate_assertion_sets(db, review_set, payload.right_assertion_set_ids or [])

    configuration = _plan_configuration(payload, comparison_type)
    name = sanitize_text(payload.name)
    if not name:
        raise _unprocessable("Comparison plan name is required")

    plan = PreconstructionComparisonPlan(
        project_id=review_set.project_id,
        review_set_id=review_set.id,
        name=name,
        normalized_name=_normalized_name(name),
        description=sanitize_text(payload.description),
        comparison_type=comparison_type.value,
        status="draft",
        taxonomy_version=taxonomy.TAXONOMY_VERSION,
        left_role_filters=_canonical(configuration["left_role_filters"]),
        right_role_filters=_canonical(configuration["right_role_filters"]),
        left_assertion_set_ids=_canonical(configuration["left_assertion_set_ids"]),
        right_assertion_set_ids=_canonical(configuration["right_assertion_set_ids"]),
        include_manual_assertions=configuration["include_manual_assertions"],
        minimum_review_state=configuration["minimum_review_state"],
        configuration_json=_canonical(configuration),
        configuration_hash=_canonical_hash(configuration),
        created_by=user_id,
    )
    db.add(plan)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict(
            "A comparison plan with this name already exists"
        ) from error
    db.refresh(plan)
    return plan


def update_comparison_plan(
    db: Session,
    review_set: PreconstructionReviewSet,
    plan: PreconstructionComparisonPlan,
    payload,
) -> PreconstructionComparisonPlan:
    _require_editable_plan(plan)
    comparison_type = resolve_comparison_type(
        payload.comparison_type or plan.comparison_type
    )
    if comparison_type is None:
        raise _unprocessable("Unknown comparison type")

    merged = _MergedPlanPayload(plan, payload, comparison_type)
    _validate_assertion_sets(db, review_set, merged.left_assertion_set_ids)
    _validate_assertion_sets(db, review_set, merged.right_assertion_set_ids)
    configuration = _plan_configuration(merged, comparison_type)

    if payload.name is not None:
        name = sanitize_text(payload.name)
        if not name:
            raise _unprocessable("Comparison plan name is required")
        plan.name = name
        plan.normalized_name = _normalized_name(name)
    if payload.description is not None:
        plan.description = sanitize_text(payload.description)
    plan.comparison_type = comparison_type.value
    plan.left_role_filters = _canonical(configuration["left_role_filters"])
    plan.right_role_filters = _canonical(configuration["right_role_filters"])
    plan.left_assertion_set_ids = _canonical(configuration["left_assertion_set_ids"])
    plan.right_assertion_set_ids = _canonical(configuration["right_assertion_set_ids"])
    plan.include_manual_assertions = configuration["include_manual_assertions"]
    plan.minimum_review_state = configuration["minimum_review_state"]
    plan.configuration_json = _canonical(configuration)
    plan.configuration_hash = _canonical_hash(configuration)
    plan.updated_at = utc_now()
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict("A comparison plan with this name already exists") from error
    db.refresh(plan)
    return plan


class _MergedPlanPayload:
    """Merge a partial update onto the stored plan for revalidation."""

    def __init__(self, plan, payload, comparison_type):
        self.name = payload.name if payload.name is not None else plan.name
        self.description = (
            payload.description if payload.description is not None else plan.description
        )
        self.comparison_type = comparison_type.value
        self.left_role_filters = (
            payload.left_role_filters
            if payload.left_role_filters is not None
            else _json_list(plan.left_role_filters)
        )
        self.right_role_filters = (
            payload.right_role_filters
            if payload.right_role_filters is not None
            else _json_list(plan.right_role_filters)
        )
        self.left_assertion_set_ids = (
            payload.left_assertion_set_ids
            if payload.left_assertion_set_ids is not None
            else _json_list(plan.left_assertion_set_ids)
        )
        self.right_assertion_set_ids = (
            payload.right_assertion_set_ids
            if payload.right_assertion_set_ids is not None
            else _json_list(plan.right_assertion_set_ids)
        )
        self.include_manual_assertions = (
            payload.include_manual_assertions
            if payload.include_manual_assertions is not None
            else plan.include_manual_assertions
        )
        self.minimum_review_state = (
            payload.minimum_review_state
            if payload.minimum_review_state is not None
            else plan.minimum_review_state
        )


def archive_comparison_plan(
    db: Session, plan: PreconstructionComparisonPlan
) -> PreconstructionComparisonPlan:
    if plan.status == "archived":
        raise _conflict("Comparison plan is already archived")
    plan.status = "archived"
    plan.archived_at = utc_now()
    plan.updated_at = utc_now()
    db.commit()
    db.refresh(plan)
    return plan


def list_comparison_plans(
    db: Session, project_id: int, review_set_id: int, *, limit: int, offset: int
) -> tuple[list[PreconstructionComparisonPlan], int]:
    query = db.query(PreconstructionComparisonPlan).filter(
        PreconstructionComparisonPlan.project_id == project_id,
        PreconstructionComparisonPlan.review_set_id == review_set_id,
    )
    total = query.with_entities(func.count(PreconstructionComparisonPlan.id)).scalar()
    items = (
        query.order_by(
            PreconstructionComparisonPlan.created_at.desc(),
            PreconstructionComparisonPlan.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def comparison_plan_response(plan: PreconstructionComparisonPlan) -> dict:
    comparison_type = resolve_comparison_type(plan.comparison_type)
    return {
        "id": plan.id,
        "project_id": plan.project_id,
        "review_set_id": plan.review_set_id,
        "name": plan.name,
        "description": plan.description,
        "comparison_type": plan.comparison_type,
        "comparison_type_label": (
            comparison_type.label if comparison_type else plan.comparison_type
        ),
        "comparison_type_description": (
            comparison_type.description if comparison_type else None
        ),
        "revision_lineage": bool(comparison_type and comparison_type.revision_lineage),
        "status": plan.status,
        "status_label": plan.status.replace("_", " ").title(),
        "taxonomy_version": plan.taxonomy_version,
        "left_role_filters": _json_list(plan.left_role_filters),
        "right_role_filters": _json_list(plan.right_role_filters),
        "left_assertion_set_ids": _json_list(plan.left_assertion_set_ids),
        "right_assertion_set_ids": _json_list(plan.right_assertion_set_ids),
        "include_manual_assertions": plan.include_manual_assertions,
        "minimum_review_state": plan.minimum_review_state,
        "configuration_hash": plan.configuration_hash,
        "created_by": plan.created_by,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "locked_at": plan.locked_at,
        "archived_at": plan.archived_at,
        "editable": plan.status in ("draft", "ready"),
    }


def comparison_type_catalog() -> list[dict]:
    return [comparison_type_payload(item) for item in COMPARISON_TYPES]


# ---------------------------------------------------------------------------
# Eligible assertion resolution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EligibleAssertion:
    assertion: PreconstructionScopeAssertion
    review_id: int | None
    source: PreconstructionReviewSource
    comparable: ComparableAssertion


def _latest_review_ids(db: Session, assertion_ids: list[int]) -> dict[int, int]:
    if not assertion_ids:
        return {}
    latest = (
        select(func.max(PreconstructionAssertionReview.id))
        .where(PreconstructionAssertionReview.assertion_id.in_(assertion_ids))
        .group_by(PreconstructionAssertionReview.assertion_id)
    )
    return {
        review.assertion_id: review.id
        for review in db.query(PreconstructionAssertionReview)
        .filter(PreconstructionAssertionReview.id.in_(latest))
        .all()
    }


def _comparable(
    assertion: PreconstructionScopeAssertion,
    source: PreconstructionReviewSource,
    review_id: int | None,
    evidence_ids: tuple[int, ...],
    revision_ordinal: int | None,
) -> ComparableAssertion:
    return ComparableAssertion(
        assertion_id=assertion.id,
        review_id=review_id,
        source_id=assertion.source_id,
        document_role=source.document_role,
        concept_code=assertion.concept_code,
        assertion_type=assertion.assertion_type,
        inclusion_state=assertion.inclusion_state,
        subject=assertion.subject,
        normalized_subject=normalized_comparison_text(assertion.subject),
        normalized_requirement=assertion.normalized_requirement or "",
        responsibility_party=assertion.responsibility_party,
        discipline=assertion.discipline,
        trade=assertion.trade,
        specification_section=assertion.specification_section,
        drawing_sheet=assertion.drawing_sheet or source.sheet_number_snapshot,
        quantity_value=assertion.quantity_value,
        quantity_unit=assertion.quantity_unit,
        location_text=assertion.location_text,
        origin=assertion.origin,
        content_hash="",
        evidence_ids=evidence_ids,
        drawing_revision_id=source.drawing_revision_id,
        revision_code=source.revision_code_snapshot,
        revision_ordinal=revision_ordinal,
    )


@dataclass(frozen=True)
class ResolvedPopulation:
    """One resolution of a plan's eligible assertions, safe to reuse.

    A comparison request previously resolved the same population twice: once
    for readiness and once for candidate generation. Resolving once and passing
    the result through is purely a cost change — the inputs, ordering, and
    resulting manifest are identical either way.
    """

    left: list[EligibleAssertion]
    right: list[EligibleAssertion]
    warnings: list[str]
    resolve_ms: int = 0


def resolve_population(
    db: Session,
    plan: PreconstructionComparisonPlan,
    config: PreconstructionComparisonConfig,
) -> ResolvedPopulation:
    started = perf_counter()
    left, right, warnings = resolve_eligible_assertions(db, plan, config)
    return ResolvedPopulation(
        left=left,
        right=right,
        warnings=warnings,
        resolve_ms=int(max(0.0, perf_counter() - started) * 1000),
    )


def resolve_eligible_assertions(
    db: Session,
    plan: PreconstructionComparisonPlan,
    config: PreconstructionComparisonConfig,
) -> tuple[list[EligibleAssertion], list[EligibleAssertion], list[str]]:
    """Resolve the exact left and right assertion populations for a plan.

    Only human-reviewed assertions in the configured minimum review state are
    eligible. Proposed, rejected, and superseded assertions are always
    excluded, as are assertions outside the selected assertion sets.
    """
    comparison_type = resolve_comparison_type(plan.comparison_type)
    if comparison_type is None:
        raise _unprocessable("Unknown comparison type")

    eligible_statuses = ELIGIBLE_STATUSES_BY_MINIMUM[plan.minimum_review_state]
    left_roles = _json_list(plan.left_role_filters) or list(comparison_type.left_roles)
    right_roles = _json_list(plan.right_role_filters) or list(comparison_type.right_roles)
    left_sets = _json_list(plan.left_assertion_set_ids)
    right_sets = _json_list(plan.right_assertion_set_ids)

    query = (
        db.query(PreconstructionScopeAssertion, PreconstructionReviewSource)
        .join(
            PreconstructionReviewSource,
            PreconstructionReviewSource.id == PreconstructionScopeAssertion.source_id,
        )
        .filter(
            PreconstructionScopeAssertion.project_id == plan.project_id,
            PreconstructionScopeAssertion.review_set_id == plan.review_set_id,
            PreconstructionScopeAssertion.status.in_(eligible_statuses),
        )
    )
    if not plan.include_manual_assertions:
        query = query.filter(PreconstructionScopeAssertion.origin != "manual")
    rows = query.order_by(PreconstructionScopeAssertion.id.asc()).limit(
        config.max_assertions_per_comparison + 1
    ).all()

    warnings: list[str] = []
    if len(rows) > config.max_assertions_per_comparison:
        warnings.append("assertion_limit_reached")
        rows = rows[: config.max_assertions_per_comparison]

    assertion_ids = [assertion.id for assertion, _ in rows]
    review_ids = _latest_review_ids(db, assertion_ids)
    evidence_rows = (
        db.query(
            PreconstructionAssertionEvidence.assertion_id,
            PreconstructionAssertionEvidence.id,
        )
        .filter(
            PreconstructionAssertionEvidence.project_id == plan.project_id,
            PreconstructionAssertionEvidence.assertion_id.in_(assertion_ids),
        )
        .order_by(PreconstructionAssertionEvidence.id.asc())
        .all()
        if assertion_ids
        else []
    )
    evidence_by_assertion: dict[int, list[int]] = {}
    for assertion_id, evidence_id in evidence_rows:
        evidence_by_assertion.setdefault(assertion_id, []).append(evidence_id)

    left: list[EligibleAssertion] = []
    right: list[EligibleAssertion] = []
    stale = 0
    unsupported_taxonomy = 0

    for assertion, source in rows:
        if assertion.taxonomy_version != taxonomy.TAXONOMY_VERSION:
            unsupported_taxonomy += 1
            continue
        evidence_ids = tuple(evidence_by_assertion.get(assertion.id, ()))
        if not evidence_ids:
            # An assertion whose evidence has become unavailable cannot be
            # compared; it is counted rather than silently dropped.
            stale += 1
            continue
        item = EligibleAssertion(
            assertion=assertion,
            review_id=review_ids.get(assertion.id),
            source=source,
            comparable=_comparable(
                assertion, source, review_ids.get(assertion.id), evidence_ids,
                source.drawing_revision_id,
            ),
        )
        if left_sets and assertion.assertion_set_id not in left_sets:
            in_left = False
        else:
            in_left = source.document_role in left_roles
        if right_sets and assertion.assertion_set_id not in right_sets:
            in_right = False
        else:
            in_right = source.document_role in right_roles
        if in_left:
            left.append(item)
        if in_right:
            right.append(item)

    if stale:
        warnings.append(f"stale_assertion_evidence:{stale}")
    if unsupported_taxonomy:
        warnings.append(f"unsupported_taxonomy_version:{unsupported_taxonomy}")
    return left, right, warnings


# ---------------------------------------------------------------------------
# Comparison manifest
# ---------------------------------------------------------------------------

def build_comparison_manifest(
    plan: PreconstructionComparisonPlan,
    left: list[EligibleAssertion],
    right: list[EligibleAssertion],
    provider_profile: str,
    config: PreconstructionComparisonConfig,
) -> tuple[dict, str]:
    """Deterministic manifest pinning assertions, reviews, and evidence.

    Contains no assertion text, no segment text, no provider response, no
    storage metadata, and no credentials. Uses its own version and hash: the
    M18.1 analysis-manifest formula is untouched.
    """

    def entry(item: EligibleAssertion, side: str) -> dict:
        return {
            "side": side,
            "assertion_id": item.assertion.id,
            "assertion_set_id": item.assertion.assertion_set_id,
            "review_id": item.review_id,
            "review_status": item.assertion.status,
            "origin": item.assertion.origin,
            "concept_code": item.assertion.concept_code,
            "taxonomy_version": item.assertion.taxonomy_version,
            "source_id": item.assertion.source_id,
            "document_role": item.source.document_role,
            "source_checksum": item.source.source_checksum,
            "evidence_ids": list(item.comparable.evidence_ids),
        }

    payload = {
        "manifest_version": config.manifest_version,
        "schema_version": config.schema_version,
        "template_version": config.template_version,
        "comparison_plan_id": plan.id,
        "comparison_type": plan.comparison_type,
        "review_set_id": plan.review_set_id,
        "taxonomy_version": plan.taxonomy_version,
        "configuration_hash": plan.configuration_hash,
        "provider_profile": provider_profile,
        "left": sorted(
            (entry(item, "left") for item in left),
            key=lambda row: row["assertion_id"],
        ),
        "right": sorted(
            (entry(item, "right") for item in right),
            key=lambda row: row["assertion_id"],
        ),
    }
    serialized = _canonical(payload)
    if len(serialized.encode("utf-8")) > config.max_result_bytes:
        raise _unprocessable("Comparison manifest exceeds the configured size limit")
    return payload, sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

def comparison_readiness(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    config: PreconstructionComparisonConfig,
    *,
    provider_available: bool,
    provider_profile: str,
    population: "ResolvedPopulation | None" = None,
    execution_config: PreconstructionExecutionConfig | None = None,
) -> dict:
    """Deterministic readiness. Never executes a provider.

    ``population`` lets a caller that has already resolved the plan's eligible
    assertions pass that result in rather than resolving it a second time.
    """
    comparison_type = resolve_comparison_type(plan.comparison_type)
    blockers: list[str] = []
    warnings: list[str] = []

    if population is None:
        population = resolve_population(db, plan, config)
    left, right, resolution_warnings = (
        population.left,
        population.right,
        population.warnings,
    )
    for warning in resolution_warnings:
        if warning.startswith("stale_assertion_evidence"):
            warnings.append(
                f"{warning.split(':')[1]} accepted assertion(s) have no available "
                "evidence and are excluded."
            )
        elif warning.startswith("unsupported_taxonomy_version"):
            warnings.append(
                f"{warning.split(':')[1]} assertion(s) pin an unsupported taxonomy "
                "version and are excluded."
            )
        else:
            warnings.append("The assertion limit for one comparison was reached.")

    if comparison_type is None:
        blockers.append("The configured comparison type is unavailable.")
    if plan.status == "archived":
        blockers.append("Archived comparison plans cannot start comparison runs.")
    if review_set.status == "archived":
        blockers.append("Archived review sets cannot start comparison runs.")
    if plan.taxonomy_version != taxonomy.TAXONOMY_VERSION:
        blockers.append("The comparison plan pins an unsupported taxonomy version.")
    if not left:
        blockers.append("No accepted requirement-side assertions are available.")
    if not right and comparison_type and comparison_type.require_right:
        blockers.append("No accepted coverage-side assertions are available.")
    if len(left) + len(right) > config.max_assertions_per_comparison:
        blockers.append("The comparison exceeds the configured assertion limit.")

    if plan.minimum_review_state == "accepted":
        warnings.append("Needs-review assertions are excluded from this comparison.")
    else:
        warnings.append("Needs-review assertions are included in this comparison.")
    if not plan.include_manual_assertions:
        warnings.append("Human-authored assertions are excluded from this comparison.")
    if comparison_type and comparison_type.revision_lineage:
        sheets_left = {item.comparable.drawing_sheet for item in left}
        sheets_right = {item.comparable.drawing_sheet for item in right}
        if not (sheets_left & sheets_right):
            warnings.append(
                "No shared drawing sheet was found across the selected revisions."
            )
    if not provider_available:
        warnings.append(
            "Provider validation is unavailable; deterministic comparison remains "
            "available."
        )

    execution_config = execution_config or PRECONSTRUCTION_EXECUTION_CONFIG
    budget = estimate_pair_budget(
        len(left),
        0 if (comparison_type and comparison_type.revision_lineage) else len(right),
        execution_config.max_comparison_pairs,
    )
    if not budget.within_budget:
        blockers.append(
            "The comparison exceeds the configured pair budget; narrow the plan's "
            "role or assertion-set filters."
        )

    return {
        "ready": not blockers,
        "blockers": blockers[:50],
        "warnings": warnings[:50],
        "comparison_type": plan.comparison_type,
        "requirement_assertion_count": len(left),
        "coverage_assertion_count": len(right),
        "accepted_assertion_count": len(
            {item.assertion.id for item in (*left, *right)}
        ),
        "stale_assertion_count": sum(
            int(item.split(":")[1])
            for item in resolution_warnings
            if item.startswith("stale_assertion_evidence")
        ),
        "unsupported_taxonomy_count": sum(
            int(item.split(":")[1])
            for item in resolution_warnings
            if item.startswith("unsupported_taxonomy_version")
        ),
        "deterministic_comparison_available": not blockers,
        "provider_validation_available": bool(
            provider_available
            and comparison_type
            and comparison_type.provider_validation_eligible
        ),
        "provider_profile": provider_profile,
        "taxonomy_version": taxonomy.TAXONOMY_VERSION,
        # Bounded, text-free execution diagnostics. Deliberately free of any
        # measured duration: readiness is deterministic, so identical inputs
        # must produce a byte-identical response. Timings live on the execution
        # metric record instead.
        "diagnostics": (
            {
                "pair_budget": budget.payload(),
                "persist_chunk_size": execution_config.persist_chunk_size,
                "finding_evidence_limit": execution_config.finding_evidence_limit,
                "metrics_enabled": execution_config.metrics_enabled,
            }
            if execution_config.diagnostics_enabled
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

@dataclass
class ComparisonExecution:
    plan: PreconstructionComparisonPlan
    manifest: dict
    manifest_hash: str
    candidates: list[Candidate]
    warnings: list[str]
    by_assertion: dict[int, EligibleAssertion]
    timer: PhaseTimer | None = None
    budget_stop_reason: str | None = None


def generate_candidates(
    db: Session,
    plan: PreconstructionComparisonPlan,
    config: PreconstructionComparisonConfig,
    provider_profile: str,
    *,
    population: ResolvedPopulation | None = None,
    execution_config: PreconstructionExecutionConfig | None = None,
    timer: PhaseTimer | None = None,
) -> ComparisonExecution:
    comparison_type = resolve_comparison_type(plan.comparison_type)
    execution_config = execution_config or PRECONSTRUCTION_EXECUTION_CONFIG
    timer = timer or PhaseTimer()

    if population is None:
        with timer.measure("resolve"):
            population = resolve_population(db, plan, config)
    else:
        timer.record("resolve", population.resolve_ms / 1000)
    left, right, warnings = population.left, population.right, list(population.warnings)

    with timer.measure("manifest"):
        manifest, manifest_hash = build_comparison_manifest(
            plan, left, right, provider_profile, config
        )
    by_assertion = {item.assertion.id: item for item in (*left, *right)}

    revision_lineage = bool(comparison_type and comparison_type.revision_lineage)
    budget_stop_reason: str | None = None
    if not revision_lineage:
        budget = estimate_pair_budget(
            len(left), len(right), execution_config.max_comparison_pairs
        )
        if not budget.within_budget:
            # Refuse rather than silently truncating a population the operator
            # believes was compared in full.
            raise _unprocessable(
                "The comparison exceeds the configured pair budget "
                f"({budget.estimated_pairs} pairs > {budget.maximum_pairs})"
            )

    with timer.measure("match"):
        if revision_lineage:
            candidates, generation_warnings = generate_revision_candidates(
                [item.comparable for item in left],
                [item.comparable for item in right],
                maximum_candidates=config.max_candidates_per_run,
            )
        else:
            candidates, generation_warnings = generate_coverage_candidates(
                [item.comparable for item in left],
                [item.comparable for item in right],
                covered_minimum=config.covered_minimum_match_class,
                maximum_candidates=config.max_candidates_per_run,
            )

    if "candidate_limit_reached" in generation_warnings:
        budget_stop_reason = "candidate_limit_reached"

    filtered = [
        candidate
        for candidate in candidates
        if finding_type_allowed(plan.comparison_type, candidate.finding_type)
    ]
    if len(filtered) != len(candidates):
        generation_warnings.append("finding_type_not_allowed_for_comparison_type")

    return ComparisonExecution(
        plan=plan,
        manifest=manifest,
        manifest_hash=manifest_hash,
        candidates=_deduplicate(filtered, generation_warnings),
        warnings=[*warnings, *generation_warnings],
        by_assertion=by_assertion,
        timer=timer,
        budget_stop_reason=budget_stop_reason,
    )


def _deduplicate(candidates: list[Candidate], warnings: list[str]) -> list[Candidate]:
    """Deterministic deduplication bounded to one finding set."""
    seen: dict[tuple, Candidate] = {}
    duplicates = 0
    for candidate in candidates:
        identity = (
            candidate.finding_type,
            tuple(sorted(candidate.requirement_assertion_ids)),
            tuple(sorted(candidate.coverage_assertion_ids)),
            normalized_comparison_text(candidate.title),
        )
        if identity in seen:
            duplicates += 1
            continue
        seen[identity] = candidate
    if duplicates:
        warnings.append(f"duplicate_candidates_merged:{duplicates}")
    return list(seen.values())


# ---------------------------------------------------------------------------
# Provider validation
# ---------------------------------------------------------------------------

def build_provider_request(
    execution: ComparisonExecution,
    config: PreconstructionComparisonConfig,
    *,
    template_version: str,
    schema_version: str,
    provider_profile: str,
    evidence_by_assertion: dict[int, list],
) -> ProviderRequest:
    comparison_type = resolve_comparison_type(execution.plan.comparison_type)
    referenced = sorted(
        {
            assertion_id
            for candidate in execution.candidates
            for assertion_id in (
                *candidate.requirement_assertion_ids,
                *candidate.coverage_assertion_ids,
            )
        }
    )
    assertions = []
    characters = 0
    for assertion_id in referenced:
        item = execution.by_assertion.get(assertion_id)
        if item is None:
            continue
        excerpts = []
        for evidence in evidence_by_assertion.get(assertion_id, [])[:5]:
            if characters + len(evidence.excerpt) > config.request_max_content_characters:
                break
            characters += len(evidence.excerpt)
            excerpts.append((evidence.id, evidence.excerpt))
        assertions.append(
            ProviderComparisonAssertion(
                assertion_id=assertion_id,
                side="requirement"
                if any(
                    assertion_id in candidate.requirement_assertion_ids
                    for candidate in execution.candidates
                )
                else "coverage",
                document_role=item.source.document_role,
                concept_code=item.assertion.concept_code,
                assertion_type=item.assertion.assertion_type,
                inclusion_state=item.assertion.inclusion_state,
                untrusted_subject=item.assertion.subject,
                untrusted_requirement=item.assertion.requirement_text or "",
                responsibility_party=item.assertion.responsibility_party,
                discipline=item.assertion.discipline,
                trade=item.assertion.trade,
                specification_section=item.assertion.specification_section,
                drawing_sheet=item.assertion.drawing_sheet,
                quantity=(
                    f"{item.assertion.quantity_value} {item.assertion.quantity_unit}"
                    if item.assertion.quantity_value is not None
                    else None
                ),
                location_text=item.assertion.location_text,
                evidence=tuple(excerpts),
            )
        )

    return ProviderRequest(
        manifest_hash=execution.manifest_hash,
        analysis_type="scope_comparison_validation",
        provider_profile=provider_profile,
        template_version=template_version,
        schema_version=schema_version,
        sources=(),
        comparison_type=execution.plan.comparison_type,
        comparison_manifest_hash=execution.manifest_hash,
        comparison_schema_version=config.schema_version,
        taxonomy_version=taxonomy.TAXONOMY_VERSION,
        allowed_finding_types=tuple(comparison_type.allowed_finding_types)
        if comparison_type
        else (),
        allowed_severities=tuple(FINDING_SEVERITIES),
        comparison_candidates=tuple(
            ProviderComparisonCandidate(
                candidate_key=candidate.candidate_key,
                finding_type=candidate.finding_type,
                default_severity=default_severity(candidate.finding_type),
                match_class=candidate.match_class,
                match_score=candidate.match_score,
                match_reasons=candidate.match_reasons,
                title=candidate.title,
                summary=candidate.summary,
                requirement_assertion_ids=candidate.requirement_assertion_ids,
                coverage_assertion_ids=candidate.coverage_assertion_ids,
            )
            for candidate in execution.candidates
        ),
        comparison_assertions=tuple(assertions),
        total_content_characters=characters,
    )


def _reject(code: str, message: str) -> ProviderError:
    return ProviderError(code, message, retryable=False)


def validate_provider_comparison(
    execution: ComparisonExecution,
    payload: dict,
    config: PreconstructionComparisonConfig,
) -> tuple[dict[str, dict], list[str]]:
    """Validate a provider comparison result against the pinned candidates.

    A provider may only disposition candidates it was given. Forged candidate
    keys, forged assertion ids, forged evidence ids, unknown finding types, and
    oversized results all reject the entire result.
    """
    try:
        parsed = ProviderComparisonResult.model_validate(payload)
    except ValidationError as error:
        raise _reject(
            "invalid_comparison_result",
            "AI provider returned an invalid comparison result",
        ) from error

    if parsed.schema_version != config.schema_version:
        raise _reject("invalid_comparison_result", "Comparison schema version mismatch")
    if parsed.taxonomy_version != taxonomy.TAXONOMY_VERSION:
        raise _reject("invalid_comparison_result", "Comparison taxonomy version mismatch")
    if parsed.comparison_type != execution.plan.comparison_type:
        raise _reject("invalid_comparison_result", "Comparison type mismatch")
    if len(parsed.candidates) > config.max_candidates_per_run:
        raise _reject("comparison_result_too_large", "Comparison result exceeded limits")

    candidates_by_key = {
        candidate.candidate_key: candidate for candidate in execution.candidates
    }
    allowed_assertion_ids = set(execution.by_assertion)
    dispositions: dict[str, dict] = {}
    warnings = list(parsed.warnings)

    for item in parsed.candidates:
        candidate = candidates_by_key.get(item.candidate_key)
        if candidate is None:
            raise _reject(
                "invalid_comparison_candidate",
                "Provider referenced an unknown comparison candidate",
            )
        if item.candidate_key in dispositions:
            raise _reject(
                "invalid_comparison_result",
                "Provider repeated a comparison candidate",
            )
        finding_type = item.finding_type or candidate.finding_type
        if finding_type not in FINDING_TYPES:
            raise _reject(
                "unknown_finding_type", "Provider proposed an unknown finding type"
            )
        if not finding_type_allowed(execution.plan.comparison_type, finding_type):
            raise _reject(
                "unknown_finding_type",
                "Provider proposed a finding type outside this comparison type",
            )
        for assertion_id in (
            *item.requirement_assertion_ids,
            *item.coverage_assertion_ids,
        ):
            if assertion_id not in allowed_assertion_ids:
                raise _reject(
                    "invalid_comparison_assertion",
                    "Provider referenced an assertion outside the pinned manifest",
                )
        allowed_evidence = {
            evidence_id
            for assertion_id in (
                *candidate.requirement_assertion_ids,
                *candidate.coverage_assertion_ids,
            )
            for evidence_id in execution.by_assertion[assertion_id].comparable.evidence_ids
        }
        for reference in item.evidence_refs:
            if reference.assertion_id not in allowed_assertion_ids:
                raise _reject(
                    "invalid_comparison_evidence",
                    "Provider referenced evidence outside the pinned manifest",
                )
            if reference.assertion_evidence_id not in allowed_evidence:
                raise _reject(
                    "invalid_comparison_evidence",
                    "Provider referenced evidence not attached to this candidate",
                )
        dispositions[item.candidate_key] = {
            "disposition": item.disposition,
            "finding_type": finding_type,
            "severity": normalize_provider_severity(finding_type, item.severity),
            "title": sanitize_text(item.title),
            "summary": sanitize_text(item.summary),
            "rationale": sanitize_text(item.rationale),
            "confidence": item.confidence,
            "confidence_basis": sanitize_text(item.confidence_basis),
        }
    return dispositions, warnings[:20]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _finding_content_hash(
    manifest_hash: str, rows: list[dict], links: list[dict], evidence: list[dict]
) -> str:
    """Deterministic hash over normalized finding content and lineage."""
    return _canonical_hash(
        {
            "manifest_hash": manifest_hash,
            "findings": sorted(
                (
                    {
                        "finding_key": row["finding_key"],
                        "finding_type": row["finding_type"],
                        "severity": row["severity"],
                        "origin": row["origin"],
                        "title": normalized_comparison_text(row["title"]),
                        "summary": normalized_comparison_text(row["summary"]),
                        "rationale": normalized_comparison_text(row["rationale"]),
                        "provider_disposition": row.get("provider_disposition"),
                        "assertions": sorted(
                            (link["assertion_id"], link["side"], link["link_role"])
                            for link in links
                            if link["finding_key"] == row["finding_key"]
                        ),
                        "evidence": sorted(
                            (item["assertion_evidence_id"], item["evidence_role"])
                            for item in evidence
                            if item["finding_key"] == row["finding_key"]
                        ),
                    }
                    for row in rows
                ),
                key=lambda row: row["finding_key"],
            ),
        }
    )


def persist_finding_set(
    db: Session,
    execution: ComparisonExecution,
    config: PreconstructionComparisonConfig,
    *,
    provider_profile: str,
    analysis_run_id: int | None,
    dispositions: dict[str, dict] | None = None,
    extra_warnings: list[str] | None = None,
    execution_config: PreconstructionExecutionConfig | None = None,
) -> PreconstructionFindingSet:
    """Persist one immutable finding set inside the caller's transaction.

    Rows are written in bounded chunks so a large finding set never builds one
    unbounded statement.
    """
    now = utc_now()
    warnings = [*execution.warnings, *(extra_warnings or [])]
    origin = "provider_validated" if dispositions is not None else "deterministic"

    evidence_rows_by_assertion = _evidence_by_assertion(
        db, execution.plan.project_id, sorted(execution.by_assertion)
    )

    finding_rows: list[dict] = []
    link_rows: list[dict] = []
    evidence_rows: list[dict] = []

    for candidate in execution.candidates:
        disposition = (dispositions or {}).get(candidate.candidate_key)
        if disposition and disposition["disposition"] == "reject":
            continue
        finding_type = (
            disposition["finding_type"] if disposition else candidate.finding_type
        )
        severity = (
            disposition["severity"] if disposition else default_severity(finding_type)
        )
        finding_rows.append(
            {
                "finding_key": candidate.candidate_key[:200],
                "project_id": execution.plan.project_id,
                "review_set_id": execution.plan.review_set_id,
                "comparison_plan_id": execution.plan.id,
                "finding_type": finding_type,
                "severity": severity,
                "title": (disposition or {}).get("title") or candidate.title,
                "summary": (disposition or {}).get("summary") or candidate.summary,
                "rationale": (disposition or {}).get("rationale") or candidate.rationale,
                "origin": origin,
                "deterministic_match_class": candidate.match_class,
                "deterministic_match_score": candidate.match_score,
                "match_reasons": _canonical(list(candidate.match_reasons)),
                "provider_disposition": (
                    disposition["disposition"] if disposition else None
                ),
                "provider_confidence": (
                    Decimal(str(disposition["confidence"])).quantize(Decimal("0.001"))
                    if disposition and disposition.get("confidence") is not None
                    else None
                ),
                "provider_confidence_basis": (
                    disposition.get("confidence_basis") if disposition else None
                ),
                "status": (
                    "needs_review"
                    if disposition
                    and disposition["disposition"] == "needs_human_review"
                    else "proposed"
                ),
                "created_by": None,
                "created_at": now,
            }
        )
        if len(finding_rows) > config.max_findings_per_set:
            warnings.append("finding_limit_reached")
            finding_rows.pop()
            break

        links = 0
        for assertion_id, side in candidate.side_by_assertion.items():
            if links >= config.max_assertion_links_per_finding:
                break
            item = execution.by_assertion.get(assertion_id)
            if item is None:
                continue
            link_rows.append(
                {
                    "finding_key": candidate.candidate_key[:200],
                    "project_id": execution.plan.project_id,
                    "assertion_id": assertion_id,
                    "assertion_review_id": item.review_id,
                    "side": side,
                    "link_role": candidate.role_by_assertion.get(assertion_id, "primary"),
                    "match_class": candidate.match_class,
                    "match_reasons": _canonical(list(candidate.match_reasons)),
                    "created_at": now,
                }
            )
            links += 1
            evidence_count = 0
            for evidence in evidence_rows_by_assertion.get(assertion_id, []):
                if evidence_count >= config.max_evidence_per_finding:
                    break
                evidence_rows.append(
                    {
                        "finding_key": candidate.candidate_key[:200],
                        "project_id": execution.plan.project_id,
                        "assertion_id": assertion_id,
                        "assertion_evidence_id": evidence.id,
                        "source_id": evidence.source_id,
                        "content_snapshot_id": evidence.content_snapshot_id,
                        "content_page_id": evidence.content_page_id,
                        "content_segment_id": evidence.content_segment_id,
                        "page_number": evidence.page_number,
                        "segment_index": evidence.segment_index,
                        "text_hash": evidence.text_hash,
                        "excerpt": evidence.excerpt,
                        "evidence_role": evidence.evidence_role,
                        "created_at": now,
                    }
                )
                evidence_count += 1

    content_hash = _finding_content_hash(
        execution.manifest_hash, finding_rows, link_rows, evidence_rows
    )
    finding_set = PreconstructionFindingSet(
        project_id=execution.plan.project_id,
        review_set_id=execution.plan.review_set_id,
        comparison_plan_id=execution.plan.id,
        analysis_run_id=analysis_run_id,
        comparison_type=execution.plan.comparison_type,
        comparison_manifest_hash=execution.manifest_hash,
        taxonomy_version=taxonomy.TAXONOMY_VERSION,
        schema_version=config.schema_version,
        provider_profile=provider_profile,
        status="completed_with_warnings" if warnings else "completed",
        candidate_count=len(execution.candidates),
        finding_count=len(finding_rows),
        warning_count=len(warnings),
        warning_codes=_canonical(warnings) if warnings else None,
        content_hash=content_hash,
        created_at=now,
        completed_at=now,
    )
    db.add(finding_set)
    db.flush()

    if not finding_rows:
        return finding_set

    chunk_size = (execution_config or PRECONSTRUCTION_EXECUTION_CONFIG).persist_chunk_size
    inserted: list = []
    for start in range(0, len(finding_rows), chunk_size):
        inserted.extend(
            db.execute(
                insert(PreconstructionFinding).returning(
                    PreconstructionFinding.id, PreconstructionFinding.finding_key
                ),
                [
                    {**row, "finding_set_id": finding_set.id}
                    for row in finding_rows[start : start + chunk_size]
                ],
            ).all()
        )
    id_by_key = {key: finding_id for finding_id, key in inserted}
    if len(id_by_key) != len(finding_rows):
        raise _reject("invalid_comparison_result", "Finding persistence was inconsistent")

    if link_rows:
        resolved_links = [
            {
                key: value
                for key, value in {**row, "finding_id": id_by_key[row["finding_key"]]}.items()
                if key != "finding_key"
            }
            for row in link_rows
            if row["finding_key"] in id_by_key
        ]
        for start in range(0, len(resolved_links), chunk_size):
            db.execute(
                insert(PreconstructionFindingAssertion),
                resolved_links[start : start + chunk_size],
            )
    if evidence_rows:
        seen: set[tuple] = set()
        deduped = []
        for row in evidence_rows:
            if row["finding_key"] not in id_by_key:
                continue
            identity = (
                id_by_key[row["finding_key"]],
                row["assertion_evidence_id"],
                row["evidence_role"],
            )
            if identity in seen:
                continue
            seen.add(identity)
            deduped.append(
                {
                    key: value
                    for key, value in {
                        **row,
                        "finding_id": id_by_key[row["finding_key"]],
                    }.items()
                    if key != "finding_key"
                }
            )
        for start in range(0, len(deduped), chunk_size):
            db.execute(
                insert(PreconstructionFindingEvidence),
                deduped[start : start + chunk_size],
            )
    return finding_set


def _evidence_by_assertion(
    db: Session, project_id: int, assertion_ids: list[int]
) -> dict[int, list[PreconstructionAssertionEvidence]]:
    if not assertion_ids:
        return {}
    rows = (
        db.query(PreconstructionAssertionEvidence)
        .filter(
            PreconstructionAssertionEvidence.project_id == project_id,
            PreconstructionAssertionEvidence.assertion_id.in_(assertion_ids),
        )
        .order_by(
            PreconstructionAssertionEvidence.assertion_id.asc(),
            PreconstructionAssertionEvidence.page_number.asc(),
            PreconstructionAssertionEvidence.segment_index.asc(),
            PreconstructionAssertionEvidence.id.asc(),
        )
        .all()
    )
    grouped: dict[int, list[PreconstructionAssertionEvidence]] = {}
    for row in rows:
        grouped.setdefault(row.assertion_id, []).append(row)
    return grouped


def comparison_run_summary(
    execution: ComparisonExecution, finding_set_id: int | None, finding_count: int
) -> dict:
    """Compact, safe run summary. Never contains finding or evidence text."""
    return {
        "analysis": "scope_comparison",
        "comparison_plan_id": execution.plan.id,
        "comparison_type": execution.plan.comparison_type,
        "finding_set_id": finding_set_id,
        "candidate_count": len(execution.candidates),
        "finding_count": finding_count,
        "comparison_manifest_hash": execution.manifest_hash,
        "warnings": execution.warnings,
    }


def find_reusable_finding_set(
    db: Session, plan: PreconstructionComparisonPlan, manifest_hash: str
) -> PreconstructionFindingSet | None:
    """The most recent completed set produced from an identical manifest.

    The comparison manifest already pins the plan, its configuration hash, the
    exact assertion ids, and the exact review that made each eligible. An
    identical hash therefore means identical inputs, so re-running would
    reproduce the same findings byte for byte. Reuse is opt-in and never
    rewrites, supersedes, or deletes the set it returns.
    """
    return (
        db.query(PreconstructionFindingSet)
        .filter(
            PreconstructionFindingSet.project_id == plan.project_id,
            PreconstructionFindingSet.comparison_plan_id == plan.id,
            PreconstructionFindingSet.comparison_manifest_hash == manifest_hash,
            PreconstructionFindingSet.status.in_(
                ("completed", "completed_with_warnings")
            ),
        )
        .order_by(
            PreconstructionFindingSet.created_at.desc(),
            PreconstructionFindingSet.id.desc(),
        )
        .first()
    )


def run_deterministic_comparison(
    db: Session,
    plan: PreconstructionComparisonPlan,
    config: PreconstructionComparisonConfig,
    *,
    population: ResolvedPopulation | None = None,
    execution_config: PreconstructionExecutionConfig | None = None,
    reuse_identical_manifest: bool = False,
) -> tuple[PreconstructionFindingSet, bool]:
    """Deterministic comparison with no provider involvement whatsoever.

    Runs in one transaction and locks the plan so later runs stay reproducible.
    Returns the finding set and whether an identical prior manifest was reused.
    """
    _require_active_plan(plan)
    execution_config = execution_config or PRECONSTRUCTION_EXECUTION_CONFIG
    timer = PhaseTimer()
    execution = generate_candidates(
        db,
        plan,
        config,
        "deterministic",
        population=population,
        execution_config=execution_config,
        timer=timer,
    )

    reused = False
    if reuse_identical_manifest:
        existing = find_reusable_finding_set(db, plan, execution.manifest_hash)
        if existing is not None:
            reused = True
            _record_comparison_metrics(
                db, plan, existing, execution, timer, execution_config, reused=True
            )
            db.commit()
            db.refresh(existing)
            return existing, True

    with timer.measure("persist"):
        finding_set = persist_finding_set(
            db,
            execution,
            config,
            provider_profile="deterministic",
            analysis_run_id=None,
            execution_config=execution_config,
        )
    if plan.status != "locked":
        plan.status = "locked"
        plan.locked_at = utc_now()
        plan.updated_at = utc_now()
    _record_comparison_metrics(
        db, plan, finding_set, execution, timer, execution_config, reused=False
    )
    db.commit()
    db.refresh(finding_set)
    return finding_set, reused


def _record_comparison_metrics(
    db: Session,
    plan: PreconstructionComparisonPlan,
    finding_set: PreconstructionFindingSet,
    execution: ComparisonExecution,
    timer: PhaseTimer,
    execution_config: PreconstructionExecutionConfig,
    *,
    reused: bool,
) -> None:
    """Append one metric row. Never restates counts the finding set owns."""
    record_execution_metrics(
        db,
        plan.project_id,
        ExecutionMetrics(
            execution_kind="scope_comparison",
            execution_id=finding_set.id,
            phase_durations=timer.payload(),
            duration_ms=timer.total_ms(),
            manifest_reused=reused,
            budget_stop_reason=execution.budget_stop_reason,
        ),
        execution_config,
    )


# ---------------------------------------------------------------------------
# Finding reads
# ---------------------------------------------------------------------------

def finding_set_response(finding_set: PreconstructionFindingSet) -> dict:
    return {
        "id": finding_set.id,
        "project_id": finding_set.project_id,
        "review_set_id": finding_set.review_set_id,
        "comparison_plan_id": finding_set.comparison_plan_id,
        "analysis_run_id": finding_set.analysis_run_id,
        "comparison_type": finding_set.comparison_type,
        "comparison_manifest_hash": finding_set.comparison_manifest_hash,
        "taxonomy_version": finding_set.taxonomy_version,
        "schema_version": finding_set.schema_version,
        "provider_profile": finding_set.provider_profile,
        "status": finding_set.status,
        "candidate_count": finding_set.candidate_count,
        "finding_count": finding_set.finding_count,
        "warning_count": finding_set.warning_count,
        "warnings": _json_list(finding_set.warning_codes),
        "content_hash": finding_set.content_hash,
        "created_at": finding_set.created_at,
        "completed_at": finding_set.completed_at,
    }


def get_finding_set(
    db: Session, project_id: int, finding_set_id: int
) -> PreconstructionFindingSet:
    finding_set = (
        db.query(PreconstructionFindingSet)
        .filter(
            PreconstructionFindingSet.id == finding_set_id,
            PreconstructionFindingSet.project_id == project_id,
        )
        .first()
    )
    if finding_set is None:
        raise _not_found("Finding set not found")
    return finding_set


def list_finding_sets(
    db: Session, project_id: int, plan_id: int, *, limit: int, offset: int
) -> tuple[list[PreconstructionFindingSet], int]:
    query = db.query(PreconstructionFindingSet).filter(
        PreconstructionFindingSet.project_id == project_id,
        PreconstructionFindingSet.comparison_plan_id == plan_id,
    )
    total = query.with_entities(func.count(PreconstructionFindingSet.id)).scalar()
    items = (
        query.order_by(
            PreconstructionFindingSet.created_at.desc(),
            PreconstructionFindingSet.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def latest_finding_set_id(db: Session, project_id: int, plan_id: int) -> int | None:
    row = (
        db.query(PreconstructionFindingSet.id)
        .filter(
            PreconstructionFindingSet.project_id == project_id,
            PreconstructionFindingSet.comparison_plan_id == plan_id,
        )
        .order_by(
            PreconstructionFindingSet.created_at.desc(),
            PreconstructionFindingSet.id.desc(),
        )
        .first()
    )
    return row[0] if row else None


def get_finding(db: Session, project_id: int, finding_id: int) -> PreconstructionFinding:
    finding = (
        db.query(PreconstructionFinding)
        .filter(
            PreconstructionFinding.id == finding_id,
            PreconstructionFinding.project_id == project_id,
        )
        .first()
    )
    if finding is None:
        raise _not_found("Finding not found")
    return finding


def list_findings(
    db: Session,
    project_id: int,
    plan_id: int,
    *,
    limit: int,
    offset: int,
    finding_set_id: int | None = None,
    finding_type: str | None = None,
    severity: str | None = None,
    review_status: str | None = None,
    origin: str | None = None,
    search: str = "",
    current_finding_set_only: bool = False,
) -> tuple[list[PreconstructionFinding], int]:
    """Allowlisted filtering with documented deterministic ordering.

    Order is review priority, then severity, then finding type, then finding id.
    """
    query = db.query(PreconstructionFinding).filter(
        PreconstructionFinding.project_id == project_id,
        PreconstructionFinding.comparison_plan_id == plan_id,
    )
    if finding_set_id is not None:
        query = query.filter(PreconstructionFinding.finding_set_id == finding_set_id)
    elif current_finding_set_only:
        current = latest_finding_set_id(db, project_id, plan_id)
        query = query.filter(
            (PreconstructionFinding.finding_set_id == current)
            | (PreconstructionFinding.finding_set_id.is_(None))
        )
    if finding_type is not None:
        query = query.filter(PreconstructionFinding.finding_type == finding_type)
    if severity is not None:
        query = query.filter(PreconstructionFinding.severity == severity)
    if review_status is not None:
        query = query.filter(PreconstructionFinding.status == review_status)
    if origin is not None:
        query = query.filter(PreconstructionFinding.origin == origin)
    normalized_search = normalized_comparison_text(search)
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.filter(
            func.lower(PreconstructionFinding.title).like(pattern)
            | func.lower(PreconstructionFinding.summary).like(pattern)
        )

    total = query.with_entities(func.count(PreconstructionFinding.id)).scalar()
    status_rank = case(
        *[
            (PreconstructionFinding.status == key, value)
            for key, value in _FINDING_STATUS_ORDER.items()
        ],
        else_=99,
    )
    severity_rank = case(
        *[
            (PreconstructionFinding.severity == key, value)
            for key, value in SEVERITY_ORDER.items()
        ],
        else_=99,
    )
    items = (
        query.order_by(
            status_rank.asc(),
            severity_rank.asc(),
            PreconstructionFinding.finding_type.asc(),
            PreconstructionFinding.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def finding_payloads(
    db: Session,
    project_id: int,
    findings: list[PreconstructionFinding],
    *,
    evidence_limit: int = 10,
) -> list[dict]:
    """Batch-resolve links, sources, evidence, and current reviews for a page.

    Query budget is fixed regardless of page size: one link query, one
    assertion query, one source query, one evidence query, one latest-review
    query.
    """
    if not findings:
        return []
    finding_ids = [item.id for item in findings]

    links = (
        db.query(PreconstructionFindingAssertion)
        .filter(
            PreconstructionFindingAssertion.project_id == project_id,
            PreconstructionFindingAssertion.finding_id.in_(finding_ids),
        )
        .order_by(
            PreconstructionFindingAssertion.finding_id.asc(),
            PreconstructionFindingAssertion.side.asc(),
            PreconstructionFindingAssertion.assertion_id.asc(),
        )
        .all()
    )
    assertion_ids = sorted({link.assertion_id for link in links})
    assertions = {
        row.id: row
        for row in db.query(PreconstructionScopeAssertion)
        .filter(
            PreconstructionScopeAssertion.project_id == project_id,
            PreconstructionScopeAssertion.id.in_(assertion_ids),
        )
        .all()
    } if assertion_ids else {}
    source_ids = sorted({row.source_id for row in assertions.values()})
    sources = {
        row.id: row
        for row in db.query(PreconstructionReviewSource)
        .filter(
            PreconstructionReviewSource.project_id == project_id,
            PreconstructionReviewSource.id.in_(source_ids),
        )
        .all()
    } if source_ids else {}

    evidence_rows = (
        db.query(PreconstructionFindingEvidence)
        .filter(
            PreconstructionFindingEvidence.project_id == project_id,
            PreconstructionFindingEvidence.finding_id.in_(finding_ids),
        )
        .order_by(
            PreconstructionFindingEvidence.finding_id.asc(),
            PreconstructionFindingEvidence.page_number.asc(),
            PreconstructionFindingEvidence.segment_index.asc(),
            PreconstructionFindingEvidence.id.asc(),
        )
        .all()
    )

    latest = (
        select(func.max(PreconstructionFindingReview.id))
        .where(PreconstructionFindingReview.finding_id.in_(finding_ids))
        .group_by(PreconstructionFindingReview.finding_id)
    )
    reviews = {
        review.finding_id: review
        for review in db.query(PreconstructionFindingReview)
        .filter(PreconstructionFindingReview.id.in_(latest))
        .all()
    }

    links_by_finding: dict[int, list] = {}
    for link in links:
        links_by_finding.setdefault(link.finding_id, []).append(link)
    evidence_by_finding: dict[int, list] = {}
    for row in evidence_rows:
        evidence_by_finding.setdefault(row.finding_id, []).append(row)

    payloads = []
    for finding in findings:
        review = reviews.get(finding.id)
        evidence = evidence_by_finding.get(finding.id, [])
        linked = []
        for link in links_by_finding.get(finding.id, []):
            assertion = assertions.get(link.assertion_id)
            source = sources.get(assertion.source_id) if assertion else None
            concept = (
                taxonomy.resolve_concept(assertion.concept_code) if assertion else None
            )
            linked.append(
                {
                    "assertion_id": link.assertion_id,
                    "side": link.side,
                    "side_label": FINDING_SIDES[link.side],
                    "link_role": link.link_role,
                    "link_role_label": FINDING_LINK_ROLES[link.link_role],
                    "match_class": link.match_class,
                    "match_class_label": MATCH_CLASSES[link.match_class],
                    "match_reasons": [
                        {"code": code, "label": MATCH_REASONS.get(code, code)}
                        for code in _json_list(link.match_reasons)
                    ],
                    "subject": assertion.subject if assertion else None,
                    "concept_code": assertion.concept_code if assertion else None,
                    "concept_name": concept.name if concept else None,
                    "concept_category_label": (
                        taxonomy.CATEGORY_LABELS[concept.category] if concept else None
                    ),
                    "inclusion_state": assertion.inclusion_state if assertion else None,
                    "responsibility_party": (
                        assertion.responsibility_party if assertion else None
                    ),
                    "quantity_value": (
                        float(assertion.quantity_value)
                        if assertion and assertion.quantity_value is not None
                        else None
                    ),
                    "quantity_unit": assertion.quantity_unit if assertion else None,
                    "location_text": assertion.location_text if assertion else None,
                    "source_id": source.id if source else None,
                    "source_display_name": (
                        source.display_name_snapshot if source else None
                    ),
                    "document_role": source.document_role if source else None,
                    "sheet_number": source.sheet_number_snapshot if source else None,
                    "revision_code": source.revision_code_snapshot if source else None,
                }
            )

        payloads.append(
            {
                "id": finding.id,
                "finding_set_id": finding.finding_set_id,
                "comparison_plan_id": finding.comparison_plan_id,
                "review_set_id": finding.review_set_id,
                "finding_type": finding.finding_type,
                "finding_type_label": FINDING_TYPES[finding.finding_type],
                "severity": finding.severity,
                "severity_label": FINDING_SEVERITIES[finding.severity],
                "title": finding.title,
                "summary": finding.summary,
                "rationale": finding.rationale,
                "origin": finding.origin,
                "origin_label": FINDING_ORIGINS[finding.origin],
                "deterministic_match_class": finding.deterministic_match_class,
                "deterministic_match_class_label": MATCH_CLASSES[
                    finding.deterministic_match_class
                ],
                "deterministic_match_score": finding.deterministic_match_score,
                "match_reasons": [
                    {"code": code, "label": MATCH_REASONS.get(code, code)}
                    for code in _json_list(finding.match_reasons)
                ],
                "provider_disposition": finding.provider_disposition,
                "provider_confidence": (
                    float(finding.provider_confidence)
                    if finding.provider_confidence is not None
                    else None
                ),
                "provider_confidence_basis": finding.provider_confidence_basis,
                "status": finding.status,
                "status_label": FINDING_STATUSES[finding.status],
                "review_decision": review.decision if review else None,
                "review_reason_code": review.reason_code if review else None,
                "review_reason_label": (
                    FINDING_REVIEW_REASON_CODES.get(review.reason_code)
                    if review and review.reason_code
                    else None
                ),
                "reviewer_note": review.reviewer_note if review else None,
                "reviewed_by": review.reviewed_by if review else None,
                "reviewed_at": review.reviewed_at if review else None,
                "supersedes_finding_id": finding.supersedes_finding_id,
                "created_at": finding.created_at,
                "assertions": linked,
                "evidence_count": len(evidence),
                "evidence": [
                    {
                        "id": item.id,
                        "assertion_id": item.assertion_id,
                        "source_id": item.source_id,
                        "source_display_name": (
                            sources[assertions[item.assertion_id].source_id].display_name_snapshot
                            if item.assertion_id in assertions
                            and assertions[item.assertion_id].source_id in sources
                            else None
                        ),
                        "snapshot_id": item.content_snapshot_id,
                        "page_number": item.page_number,
                        "segment_index": item.segment_index,
                        "excerpt": item.excerpt,
                        "evidence_role": item.evidence_role,
                        "text_hash": item.text_hash[:16],
                        "content_target": {
                            "page": "projectPreconstruction",
                            "projectId": project_id,
                            "reviewSetId": finding.review_set_id,
                            "sourceId": item.source_id,
                            "snapshotId": item.content_snapshot_id,
                            "pageNumber": item.page_number,
                        },
                    }
                    for item in evidence[:evidence_limit]
                ],
                "evidence_truncated": len(evidence) > evidence_limit,
            }
        )
    return payloads


def finding_summary_counts(db: Session, project_id: int, plan_id: int) -> dict:
    """Status, type, and origin counts in one grouped scan.

    Three separate aggregate queries previously walked the same rows three
    times. Grouping by the three columns together and folding the result in
    Python produces identical numbers from one scan.
    """
    rows = (
        db.query(
            PreconstructionFinding.status,
            PreconstructionFinding.finding_type,
            PreconstructionFinding.origin,
            func.count(PreconstructionFinding.id),
        )
        .filter(
            PreconstructionFinding.project_id == project_id,
            PreconstructionFinding.comparison_plan_id == plan_id,
        )
        .group_by(
            PreconstructionFinding.status,
            PreconstructionFinding.finding_type,
            PreconstructionFinding.origin,
        )
        .all()
    )
    statuses = {key: 0 for key in FINDING_STATUSES}
    types = {key: 0 for key in FINDING_TYPES}
    origins = {key: 0 for key in FINDING_ORIGINS}
    for status_value, type_value, origin_value, count in rows:
        statuses[status_value] = statuses.get(status_value, 0) + count
        types[type_value] = types.get(type_value, 0) + count
        origins[origin_value] = origins.get(origin_value, 0) + count
    revision_impacts = (
        types["revision_added_scope"]
        + types["revision_removed_scope"]
        + types["revision_changed_scope"]
    )
    return {
        "total": sum(statuses.values()),
        "proposed": statuses["proposed"],
        "accepted": statuses["accepted"],
        "rejected": statuses["rejected"],
        "needs_review": statuses["needs_review"],
        "intentional_exclusion": statuses["intentional_exclusion"],
        "superseded": statuses["superseded"],
        "missing_coverage": types["missing_coverage"],
        "partial_coverage": types["partial_coverage"],
        "conflicts": types["conflicting_scope"] + types["responsibility_conflict"],
        "exclusions": types["explicit_exclusion"],
        "revision_impacts": revision_impacts,
        "manual": origins["manual"],
    }


def list_finding_reviews(db: Session, project_id: int, finding_id: int) -> list[dict]:
    reviews = (
        db.query(PreconstructionFindingReview)
        .filter(
            PreconstructionFindingReview.project_id == project_id,
            PreconstructionFindingReview.finding_id == finding_id,
        )
        .order_by(
            PreconstructionFindingReview.reviewed_at.asc(),
            PreconstructionFindingReview.id.asc(),
        )
        .all()
    )
    return [
        {
            "id": review.id,
            "decision": review.decision,
            "decision_label": FINDING_REVIEW_DECISIONS[review.decision],
            "reason_code": review.reason_code,
            "reason_label": (
                FINDING_REVIEW_REASON_CODES.get(review.reason_code)
                if review.reason_code
                else None
            ),
            "reviewer_note": review.reviewer_note,
            "reviewed_by": review.reviewed_by,
            "reviewed_at": review.reviewed_at,
            "previous_review_id": review.previous_review_id,
        }
        for review in reviews
    ]


# ---------------------------------------------------------------------------
# Human review and manual authoring
# ---------------------------------------------------------------------------

def review_finding(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    finding: PreconstructionFinding,
    reviewer_id: int,
    *,
    decision: str,
    reason_code: str | None,
    reviewer_note: str | None,
    config: PreconstructionComparisonConfig,
) -> PreconstructionFindingReview:
    """Append one review event and move the server-controlled status."""
    if plan.status == "archived" or review_set.status == "archived":
        raise _conflict("Archived comparison plans are read-only")
    if finding.status == "superseded":
        raise _conflict("Superseded findings cannot be reviewed")
    if not finding_transition_allowed(finding.status, decision):
        raise _conflict(f"Cannot move a {finding.status} finding to {decision}")

    note = sanitize_text(reviewer_note)
    if note and len(note) > config.max_reviewer_note_characters:
        raise _unprocessable("Reviewer note exceeds the configured limit")
    if finding_note_required(finding.status, decision, reason_code) and not note:
        raise _unprocessable("A reviewer note is required for this decision")

    previous = (
        db.query(PreconstructionFindingReview)
        .filter(PreconstructionFindingReview.finding_id == finding.id)
        .order_by(PreconstructionFindingReview.id.desc())
        .first()
    )
    review = PreconstructionFindingReview(
        project_id=finding.project_id,
        finding_id=finding.id,
        decision=decision,
        reason_code=reason_code,
        reviewer_note=note,
        reviewed_by=reviewer_id,
        reviewed_at=utc_now(),
        previous_review_id=previous.id if previous else None,
    )
    db.add(review)
    finding.status = DECISION_TO_FINDING_STATUS[decision]
    db.commit()
    db.refresh(review)
    return review


def create_manual_finding(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    author_id: int,
    payload,
    config: PreconstructionComparisonConfig,
) -> PreconstructionFinding:
    """Create one human-authored finding with server-derived evidence.

    Manual findings carry ``origin='manual'`` and never a provider confidence.
    They start as ``accepted`` because a person is explicitly authoring and
    confirming them.
    """
    if plan.status == "archived" or review_set.status == "archived":
        raise _conflict("Archived comparison plans are read-only")
    if payload.finding_type not in FINDING_TYPES:
        raise _unprocessable("Unknown finding type")
    if not finding_type_allowed(plan.comparison_type, payload.finding_type):
        raise _unprocessable("Finding type is not permitted for this comparison type")

    existing = (
        db.query(func.count(PreconstructionFinding.id))
        .filter(
            PreconstructionFinding.project_id == plan.project_id,
            PreconstructionFinding.comparison_plan_id == plan.id,
            PreconstructionFinding.origin == "manual",
        )
        .scalar()
    )
    if existing >= config.max_manual_findings_per_plan:
        raise _conflict("Manual finding limit reached for this comparison plan")

    assertion_ids = sorted({item.assertion_id for item in payload.assertions})
    if len(assertion_ids) > config.max_assertion_links_per_finding:
        raise _unprocessable("Too many linked assertions")
    rows = (
        db.query(PreconstructionScopeAssertion)
        .filter(
            PreconstructionScopeAssertion.project_id == plan.project_id,
            PreconstructionScopeAssertion.review_set_id == plan.review_set_id,
            PreconstructionScopeAssertion.id.in_(assertion_ids),
            PreconstructionScopeAssertion.status.in_(
                ELIGIBLE_STATUSES_BY_MINIMUM[plan.minimum_review_state]
            ),
        )
        .all()
    )
    if len(rows) != len(assertion_ids):
        raise _unprocessable(
            "Linked assertions must be reviewed assertions in this review set"
        )
    assertions = {row.id: row for row in rows}

    evidence_ids = sorted(set(payload.evidence_ids or []))
    if len(evidence_ids) > config.max_evidence_per_finding:
        raise _unprocessable("Too many evidence records selected")
    evidence_rows = (
        db.query(PreconstructionAssertionEvidence)
        .filter(
            PreconstructionAssertionEvidence.project_id == plan.project_id,
            PreconstructionAssertionEvidence.id.in_(evidence_ids),
            PreconstructionAssertionEvidence.assertion_id.in_(assertion_ids),
        )
        .all()
        if evidence_ids
        else []
    )
    if len(evidence_rows) != len(evidence_ids):
        raise _unprocessable("Selected evidence must belong to the linked assertions")

    title = sanitize_text(payload.title)
    if not title:
        raise _unprocessable("A title is required")
    severity = payload.severity or default_severity(payload.finding_type)
    if severity not in FINDING_SEVERITIES:
        raise _unprocessable("Unknown severity")

    now = utc_now()
    finding = PreconstructionFinding(
        project_id=plan.project_id,
        finding_set_id=None,
        review_set_id=plan.review_set_id,
        comparison_plan_id=plan.id,
        finding_key=f"manual:{author_id}:{int(now.timestamp() * 1000)}",
        finding_type=payload.finding_type,
        severity=severity,
        title=title,
        summary=sanitize_text(payload.summary),
        rationale=sanitize_text(payload.rationale),
        origin="manual",
        deterministic_match_class="none",
        deterministic_match_score=None,
        match_reasons=None,
        provider_disposition=None,
        provider_confidence=None,
        provider_confidence_basis=None,
        status="accepted",
        created_by=author_id,
        created_at=now,
    )
    db.add(finding)
    db.flush()

    review_ids = _latest_review_ids(db, assertion_ids)
    db.execute(
        insert(PreconstructionFindingAssertion),
        [
            {
                "project_id": plan.project_id,
                "finding_id": finding.id,
                "assertion_id": item.assertion_id,
                "assertion_review_id": review_ids.get(item.assertion_id),
                "side": item.side,
                "link_role": item.link_role,
                "match_class": "none",
                "match_reasons": None,
                "created_at": now,
            }
            for item in payload.assertions
        ],
    )
    if evidence_rows:
        db.execute(
            insert(PreconstructionFindingEvidence),
            [
                {
                    "project_id": plan.project_id,
                    "finding_id": finding.id,
                    "assertion_id": row.assertion_id,
                    "assertion_evidence_id": row.id,
                    "source_id": row.source_id,
                    "content_snapshot_id": row.content_snapshot_id,
                    "content_page_id": row.content_page_id,
                    "content_segment_id": row.content_segment_id,
                    "page_number": row.page_number,
                    "segment_index": row.segment_index,
                    "text_hash": row.text_hash,
                    # Derived server-side from stored evidence, never supplied
                    # by the client.
                    "excerpt": row.excerpt,
                    "evidence_role": row.evidence_role,
                    "created_at": now,
                }
                for row in evidence_rows
            ],
        )
    db.add(
        PreconstructionFindingReview(
            project_id=plan.project_id,
            finding_id=finding.id,
            decision="accepted",
            reason_code=None,
            reviewer_note=sanitize_text(payload.reviewer_note) or "Human-authored finding",
            reviewed_by=author_id,
            reviewed_at=now,
            previous_review_id=None,
        )
    )
    db.commit()
    db.refresh(finding)
    return finding
