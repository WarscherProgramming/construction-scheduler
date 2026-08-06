"""Structured scope assertions, evidence, and human review.

Provider output is untrusted. Every concept code, source reference, and
evidence coordinate is revalidated here against the run's immutable manifest
and the pinned M18.2 content snapshot before anything is persisted. Excerpts
are always derived server-side from stored segment text; the provider never
supplies display text, review state, project identity, or database identity.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import unicodedata

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import case, func, insert, select
from sqlalchemy.orm import Session

from app.core.config import PreconstructionScopeConfig
from app.models.drawing import DrawingRevision
from app.models.preconstruction import (
    PreconstructionAnalysisRun,
    PreconstructionContentPage,
    PreconstructionContentSegment,
    PreconstructionContentSnapshot,
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)
from app.models.scope_assertion import (
    PreconstructionAssertionEvidence,
    PreconstructionAssertionReview,
    PreconstructionScopeAssertion,
    PreconstructionScopeAssertionSet,
)
from app.preconstruction import taxonomy
from app.preconstruction.assertions import (
    ASSERTION_ORIGINS,
    ASSERTION_STATUSES,
    ASSERTION_TYPES,
    DECISION_TO_STATUS,
    EVIDENCE_ROLES,
    INCLUSION_STATES,
    REVIEW_REASON_CODES,
    assertion_status_label,
    note_required,
    review_reason_label,
    transition_allowed,
)
from app.preconstruction.provider import (
    ProviderError,
    ProviderRequest,
    ProviderScopeAssertionResult,
)


SCOPE_ANALYSIS_TYPE = "scope_assertion_extraction"
ACTIVE_REVIEW_STATUSES = ("proposed", "needs_review")
# Review-priority ordering: unreviewed work first, then settled decisions.
_STATUS_ORDER = {
    "proposed": 0,
    "needs_review": 1,
    "accepted": 2,
    "rejected": 3,
    "superseded": 4,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
    )


def _canonical_hash(payload: object) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def sanitize_text(value: str | None) -> str | None:
    """NFKC, strip unsafe control/format characters, collapse whitespace.

    Technical identifiers keep their punctuation and casing; only whitespace
    and unsafe characters are touched. Blank results become ``None``.
    """
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(
        character
        for character in normalized
        if character in {"\n", "\t", " "}
        or unicodedata.category(character) not in {"Cc", "Cf"}
    )
    collapsed = " ".join(cleaned.split())
    return collapsed or None


def normalized_comparison_text(value: str | None) -> str:
    """Case-folded, whitespace-collapsed form used for identity and search."""
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Provider result validation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidatedEvidence:
    source_id: int
    snapshot_id: int
    page_id: int
    segment_id: int
    page_number: int
    segment_index: int
    text_hash: str
    excerpt: str
    character_start: int | None
    character_end: int | None
    evidence_role: str


@dataclass
class ValidatedAssertion:
    provider_assertion_key: str
    source_id: int
    concept_code: str
    assertion_type: str
    subject: str
    requirement_text: str | None
    normalized_requirement: str | None
    responsibility_party: str | None
    discipline: str | None
    trade: str | None
    specification_section: str | None
    drawing_sheet: str | None
    quantity_value: Decimal | None
    quantity_unit: str | None
    location_text: str | None
    inclusion_state: str
    confidence: Decimal
    confidence_basis: str | None
    evidence: list[ValidatedEvidence] = field(default_factory=list)

    def identity(self) -> tuple:
        """Deterministic dedup identity. Evidence is deliberately excluded so
        that two otherwise-identical assertions merge their citations."""
        return (
            self.source_id,
            self.concept_code,
            self.assertion_type,
            normalized_comparison_text(self.subject),
            normalized_comparison_text(self.requirement_text),
            normalized_comparison_text(self.specification_section),
            normalized_comparison_text(self.drawing_sheet),
            self.inclusion_state,
        )


@dataclass
class ValidatedScopeResult:
    taxonomy_version: str
    schema_version: str
    assertions: list[ValidatedAssertion]
    warnings: list[str]
    content_hash: str


def _reject(code: str, message: str) -> ProviderError:
    """Structural integrity failures reject the entire provider result."""
    return ProviderError(code, message, retryable=False)


def validate_scope_result(
    run: PreconstructionAnalysisRun,
    request: ProviderRequest,
    payload: dict,
    config: PreconstructionScopeConfig,
) -> ValidatedScopeResult:
    """Validate, normalize, and deduplicate one provider scope result.

    Performs no database writes. Raises ``ProviderError`` when the result is
    structurally invalid, which rejects the entire result rather than
    persisting a partially trustworthy assertion set.
    """
    try:
        parsed = ProviderScopeAssertionResult.model_validate(payload)
    except ValidationError as error:
        raise _reject(
            "invalid_scope_result", "AI provider returned an invalid scope result"
        ) from error

    if parsed.schema_version != config.schema_version:
        raise _reject("invalid_scope_result", "Scope result schema version mismatch")
    if parsed.taxonomy_version != config.taxonomy_version:
        raise _reject("invalid_scope_result", "Scope result taxonomy version mismatch")
    if len(parsed.assertions) > config.max_assertions_per_run:
        raise _reject("scope_result_too_large", "Scope result exceeded assertion limits")

    manifest_source_ids = {source.source_id for source in request.sources}
    # Coordinates the provider is permitted to cite, keyed exactly as supplied.
    segments_by_coordinate = {
        (
            segment.source_id,
            segment.snapshot_id,
            segment.page_number,
            segment.segment_index,
        ): segment
        for segment in request.content_segments
    }

    warnings: list[str] = list(parsed.warnings)
    validated: list[ValidatedAssertion] = []
    total_evidence = 0
    seen_keys: set[str] = set()

    for item in parsed.assertions:
        if item.provider_assertion_key in seen_keys:
            raise _reject(
                "invalid_scope_result", "Scope result repeated a provider assertion key"
            )
        seen_keys.add(item.provider_assertion_key)

        if item.source_id not in manifest_source_ids:
            raise _reject(
                "invalid_scope_source", "Scope assertion referenced an unknown source"
            )

        concept = taxonomy.resolve_concept(item.concept_code)
        if concept is None:
            raise _reject(
                "unknown_scope_concept", "Scope assertion used an unknown concept code"
            )
        if concept.status != "active":
            raise _reject(
                "unknown_scope_concept",
                "Scope assertion used a deprecated concept code",
            )

        if len(item.evidence_refs) > config.max_evidence_per_assertion:
            raise _reject(
                "scope_result_too_large", "Scope assertion exceeded evidence limits"
            )

        evidence: list[ValidatedEvidence] = []
        seen_evidence: set[tuple[int, str]] = set()
        for reference in item.evidence_refs:
            if reference.source_id != item.source_id:
                raise _reject(
                    "invalid_scope_evidence",
                    "Scope evidence did not match its assertion source",
                )
            segment = segments_by_coordinate.get(
                (
                    reference.source_id,
                    reference.snapshot_id,
                    reference.page_number,
                    reference.segment_index,
                )
            )
            if segment is None:
                raise _reject(
                    "invalid_scope_evidence",
                    "Scope evidence referenced content outside the pinned manifest",
                )
            if segment.text_hash != reference.text_hash:
                raise _reject(
                    "invalid_scope_evidence",
                    "Scope evidence text hash did not match the immutable segment",
                )

            segment_text = segment.untrusted_text
            start = reference.character_start
            end = reference.character_end
            if start is not None and end is not None:
                if end < start or end > len(segment_text):
                    raise _reject(
                        "invalid_scope_evidence",
                        "Scope evidence offsets fell outside the segment",
                    )
                excerpt_source = segment_text[start:end]
            else:
                start = None
                end = None
                excerpt_source = segment_text
            # The excerpt is always taken from stored text, never from the
            # provider, and is bounded for display.
            excerpt = sanitize_text(excerpt_source[: config.evidence_excerpt_characters])
            if not excerpt:
                raise _reject(
                    "invalid_scope_evidence", "Scope evidence excerpt resolved to empty text"
                )

            identity = (segment.segment_id, reference.evidence_role)
            if identity in seen_evidence:
                continue
            seen_evidence.add(identity)
            evidence.append(
                ValidatedEvidence(
                    source_id=segment.source_id,
                    snapshot_id=segment.snapshot_id,
                    page_id=0,
                    segment_id=segment.segment_id,
                    page_number=segment.page_number,
                    segment_index=segment.segment_index,
                    text_hash=segment.text_hash,
                    excerpt=excerpt,
                    character_start=start,
                    character_end=end,
                    evidence_role=reference.evidence_role,
                )
            )

        if not evidence:
            raise _reject(
                "missing_scope_evidence", "Scope assertion supplied no usable evidence"
            )
        total_evidence += len(evidence)
        if total_evidence > config.max_evidence_per_result:
            raise _reject(
                "scope_result_too_large", "Scope result exceeded total evidence limits"
            )

        subject = sanitize_text(item.subject)
        if not subject:
            raise _reject("invalid_scope_result", "Scope assertion subject was empty")
        requirement = sanitize_text(item.requirement_text)
        quantity_value = _decimal(item.quantity_value)
        quantity_unit = taxonomy.normalize_unit(item.quantity_unit)
        if item.quantity_unit and quantity_unit is None:
            warnings.append("Unrecognized quantity unit was dropped")
        if quantity_value is None:
            quantity_unit = None

        validated.append(
            ValidatedAssertion(
                provider_assertion_key=item.provider_assertion_key,
                source_id=item.source_id,
                concept_code=concept.code,
                assertion_type=item.assertion_type,
                subject=subject,
                requirement_text=requirement,
                normalized_requirement=normalized_comparison_text(requirement) or None,
                responsibility_party=sanitize_text(item.responsibility_party),
                discipline=sanitize_text(item.discipline),
                trade=sanitize_text(item.trade),
                specification_section=sanitize_text(item.specification_section),
                drawing_sheet=sanitize_text(item.drawing_sheet),
                quantity_value=quantity_value,
                quantity_unit=quantity_unit,
                location_text=sanitize_text(item.location_text),
                inclusion_state=item.inclusion_state,
                confidence=Decimal(str(item.confidence)).quantize(Decimal("0.001")),
                confidence_basis=sanitize_text(item.confidence_basis),
                evidence=evidence,
            )
        )

    deduplicated, duplicate_count = _deduplicate(validated)
    if duplicate_count:
        warnings.append(
            f"{duplicate_count} duplicate assertion"
            f"{'s were' if duplicate_count != 1 else ' was'} merged"
        )

    return ValidatedScopeResult(
        taxonomy_version=parsed.taxonomy_version,
        schema_version=parsed.schema_version,
        assertions=deduplicated,
        warnings=warnings[:20],
        content_hash=_content_hash(deduplicated),
    )


def _deduplicate(
    assertions: list[ValidatedAssertion],
) -> tuple[list[ValidatedAssertion], int]:
    """Collapse identical assertions, merging their evidence deterministically.

    Deduplication is bounded to one assertion set. Cross-run and
    cross-document equivalence are deliberately out of scope.
    """
    merged: dict[tuple, ValidatedAssertion] = {}
    duplicates = 0
    for assertion in assertions:
        identity = assertion.identity()
        existing = merged.get(identity)
        if existing is None:
            merged[identity] = assertion
            continue
        duplicates += 1
        known = {(item.segment_id, item.evidence_role) for item in existing.evidence}
        for item in assertion.evidence:
            if (item.segment_id, item.evidence_role) not in known:
                existing.evidence.append(item)
                known.add((item.segment_id, item.evidence_role))
        existing.evidence.sort(
            key=lambda item: (item.page_number, item.segment_index, item.segment_id)
        )
    return list(merged.values()), duplicates


def _content_hash(assertions: list[ValidatedAssertion]) -> str:
    """Deterministic hash over normalized content and citation coordinates.

    Scoped to one review set's pinned content: it includes the review source
    and snapshot a citation belongs to, but never row identifiers generated
    while persisting this result (assertion, evidence, or page ids). Re-running
    the same manifest over the same snapshots therefore reproduces the hash
    exactly, while a different set of sources correctly hashes differently.
    """
    return _canonical_hash(
        [
            {
                "source_id": item.source_id,
                "concept_code": item.concept_code,
                "assertion_type": item.assertion_type,
                "subject": normalized_comparison_text(item.subject),
                "requirement": normalized_comparison_text(item.requirement_text),
                "specification_section": normalized_comparison_text(
                    item.specification_section
                ),
                "drawing_sheet": normalized_comparison_text(item.drawing_sheet),
                "inclusion_state": item.inclusion_state,
                "quantity_value": (
                    str(item.quantity_value) if item.quantity_value is not None else None
                ),
                "quantity_unit": item.quantity_unit,
                "evidence": sorted(
                    [
                        {
                            "snapshot_id": evidence.snapshot_id,
                            "page_number": evidence.page_number,
                            "segment_index": evidence.segment_index,
                            "text_hash": evidence.text_hash,
                            "evidence_role": evidence.evidence_role,
                        }
                        for evidence in item.evidence
                    ],
                    key=lambda entry: (
                        entry["snapshot_id"],
                        entry["page_number"],
                        entry["segment_index"],
                        entry["evidence_role"],
                    ),
                ),
            }
            for item in sorted(
                assertions,
                key=lambda item: (
                    item.source_id,
                    item.concept_code,
                    normalized_comparison_text(item.subject),
                ),
            )
        ]
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def persist_scope_assertions(
    db: Session,
    run: PreconstructionAnalysisRun,
    validated: ValidatedScopeResult,
    config: PreconstructionScopeConfig,
) -> PreconstructionScopeAssertionSet:
    """Persist one immutable assertion set inside the caller's transaction.

    The caller owns the transaction so the assertion set, the analysis
    attempt, and the run all commit together. No partial set is ever left
    behind: any failure propagates and the caller rolls back.
    """
    now = utc_now()
    assertion_set = PreconstructionScopeAssertionSet(
        project_id=run.project_id,
        analysis_run_id=run.id,
        review_set_id=run.review_set_id,
        manifest_hash=run.manifest_hash,
        taxonomy_version=validated.taxonomy_version,
        schema_version=validated.schema_version,
        provider_profile=run.provider_profile,
        status="completed_with_warnings" if validated.warnings else "completed",
        assertion_count=len(validated.assertions),
        warning_count=len(validated.warnings),
        warning_codes=json.dumps(validated.warnings) if validated.warnings else None,
        content_hash=validated.content_hash,
        created_at=now,
        completed_at=now,
    )
    db.add(assertion_set)
    db.flush()

    if not validated.assertions:
        return assertion_set

    # Resolve the owning page for each cited segment in one query.
    segment_ids = sorted(
        {evidence.segment_id for item in validated.assertions for evidence in item.evidence}
    )
    page_by_segment = {
        segment_id: page_id
        for segment_id, page_id in db.execute(
            select(
                PreconstructionContentSegment.id,
                PreconstructionContentSegment.page_id,
            ).where(
                PreconstructionContentSegment.project_id == run.project_id,
                PreconstructionContentSegment.id.in_(segment_ids),
            )
        ).all()
    }
    if len(page_by_segment) != len(segment_ids):
        raise _reject(
            "invalid_scope_evidence", "Scope evidence referenced unavailable content"
        )

    assertion_rows = [
        {
            "project_id": run.project_id,
            "assertion_set_id": assertion_set.id,
            "review_set_id": run.review_set_id,
            "source_id": item.source_id,
            "origin": "provider",
            "concept_code": item.concept_code,
            "taxonomy_version": validated.taxonomy_version,
            "assertion_type": item.assertion_type,
            "subject": item.subject,
            "requirement_text": item.requirement_text,
            "normalized_requirement": item.normalized_requirement,
            "responsibility_party": item.responsibility_party,
            "discipline": item.discipline,
            "trade": item.trade,
            "specification_section": item.specification_section,
            "drawing_sheet": item.drawing_sheet,
            "quantity_value": item.quantity_value,
            "quantity_unit": item.quantity_unit,
            "location_text": item.location_text,
            "inclusion_state": item.inclusion_state,
            "confidence": item.confidence,
            "confidence_basis": item.confidence_basis,
            "provider_assertion_key": item.provider_assertion_key,
            "status": "proposed",
            "supersedes_assertion_id": None,
            "created_by": None,
            "created_at": now,
        }
        for item in validated.assertions
    ]
    inserted = db.execute(
        insert(PreconstructionScopeAssertion).returning(
            PreconstructionScopeAssertion.id,
            PreconstructionScopeAssertion.provider_assertion_key,
        ),
        assertion_rows,
    ).all()
    assertion_id_by_key = {key: assertion_id for assertion_id, key in inserted}
    if len(assertion_id_by_key) != len(validated.assertions):
        raise _reject("invalid_scope_result", "Scope assertion persistence was inconsistent")

    evidence_rows = [
        {
            "project_id": run.project_id,
            "assertion_id": assertion_id_by_key[item.provider_assertion_key],
            "source_id": evidence.source_id,
            "content_snapshot_id": evidence.snapshot_id,
            "content_page_id": page_by_segment[evidence.segment_id],
            "content_segment_id": evidence.segment_id,
            "page_number": evidence.page_number,
            "segment_index": evidence.segment_index,
            "text_hash": evidence.text_hash,
            "excerpt": evidence.excerpt,
            "character_start": evidence.character_start,
            "character_end": evidence.character_end,
            "evidence_role": evidence.evidence_role,
            "created_at": now,
        }
        for item in validated.assertions
        for evidence in item.evidence
    ]
    if evidence_rows:
        db.execute(insert(PreconstructionAssertionEvidence), evidence_rows)
    return assertion_set


def scope_run_summary(
    validated: ValidatedScopeResult,
    assertion_set_id: int | None = None,
) -> dict:
    """Compact, safe run summary. Never contains assertion or evidence text."""
    return {
        "analysis": SCOPE_ANALYSIS_TYPE,
        "assertion_set_id": assertion_set_id,
        "assertion_count": len(validated.assertions),
        "evidence_count": sum(len(item.evidence) for item in validated.assertions),
        "taxonomy_version": validated.taxonomy_version,
        "schema_version": validated.schema_version,
        "content_hash": validated.content_hash,
        "warnings": validated.warnings,
    }


# ---------------------------------------------------------------------------
# Taxonomy API payloads
# ---------------------------------------------------------------------------

def taxonomy_payload(
    config: PreconstructionScopeConfig,
    *,
    category: str | None = None,
    scope_kind: str | None = None,
    search: str = "",
    include_deprecated: bool = False,
) -> dict:
    concepts = taxonomy.search_concepts(
        category=category,
        scope_kind=scope_kind,
        search=search,
        include_deprecated=include_deprecated,
        limit=config.taxonomy_search_limit,
    )
    return {
        "taxonomy_version": taxonomy.TAXONOMY_VERSION,
        "concepts": [taxonomy.concept_payload(concept) for concept in concepts],
        "categories": [
            {"value": value, "label": taxonomy.CATEGORY_LABELS[value]}
            for value in taxonomy.SCOPE_CATEGORIES
        ],
        "scope_kinds": [
            {"value": value, "label": taxonomy.SCOPE_KIND_LABELS[value]}
            for value in taxonomy.SCOPE_KINDS
        ],
        "assertion_types": [
            {"value": value, "label": label} for value, label in ASSERTION_TYPES.items()
        ],
        "inclusion_states": [
            {"value": value, "label": label} for value, label in INCLUSION_STATES.items()
        ],
        "evidence_roles": [
            {"value": value, "label": label} for value, label in EVIDENCE_ROLES.items()
        ],
        "review_reason_codes": [
            {"value": value, "label": label}
            for value, label in REVIEW_REASON_CODES.items()
        ],
        "total": len(concepts),
        "limit": config.taxonomy_search_limit,
    }


# ---------------------------------------------------------------------------
# Assertion set reads
# ---------------------------------------------------------------------------

def assertion_set_response(assertion_set: PreconstructionScopeAssertionSet) -> dict:
    return {
        "id": assertion_set.id,
        "project_id": assertion_set.project_id,
        "review_set_id": assertion_set.review_set_id,
        "analysis_run_id": assertion_set.analysis_run_id,
        "manifest_hash": assertion_set.manifest_hash,
        "taxonomy_version": assertion_set.taxonomy_version,
        "schema_version": assertion_set.schema_version,
        "provider_profile": assertion_set.provider_profile,
        "status": assertion_set.status,
        "assertion_count": assertion_set.assertion_count,
        "warning_count": assertion_set.warning_count,
        "warnings": (
            json.loads(assertion_set.warning_codes)
            if assertion_set.warning_codes
            else []
        ),
        "content_hash": assertion_set.content_hash,
        "created_at": assertion_set.created_at,
        "completed_at": assertion_set.completed_at,
    }


def list_assertion_sets(
    db: Session,
    project_id: int,
    review_set_id: int,
    *,
    limit: int,
    offset: int,
) -> tuple[list[PreconstructionScopeAssertionSet], int]:
    query = db.query(PreconstructionScopeAssertionSet).filter(
        PreconstructionScopeAssertionSet.project_id == project_id,
        PreconstructionScopeAssertionSet.review_set_id == review_set_id,
    )
    total = query.with_entities(
        func.count(PreconstructionScopeAssertionSet.id)
    ).scalar()
    items = (
        query.order_by(
            PreconstructionScopeAssertionSet.created_at.desc(),
            PreconstructionScopeAssertionSet.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_assertion_set(
    db: Session, project_id: int, assertion_set_id: int
) -> PreconstructionScopeAssertionSet:
    assertion_set = (
        db.query(PreconstructionScopeAssertionSet)
        .filter(
            PreconstructionScopeAssertionSet.id == assertion_set_id,
            PreconstructionScopeAssertionSet.project_id == project_id,
        )
        .first()
    )
    if assertion_set is None:
        raise _not_found("Scope assertion set not found")
    return assertion_set


def latest_assertion_set_id(
    db: Session, project_id: int, review_set_id: int
) -> int | None:
    row = (
        db.query(PreconstructionScopeAssertionSet.id)
        .filter(
            PreconstructionScopeAssertionSet.project_id == project_id,
            PreconstructionScopeAssertionSet.review_set_id == review_set_id,
        )
        .order_by(
            PreconstructionScopeAssertionSet.created_at.desc(),
            PreconstructionScopeAssertionSet.id.desc(),
        )
        .first()
    )
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Assertion reads
# ---------------------------------------------------------------------------

def get_assertion(
    db: Session, project_id: int, assertion_id: int
) -> PreconstructionScopeAssertion:
    assertion = (
        db.query(PreconstructionScopeAssertion)
        .filter(
            PreconstructionScopeAssertion.id == assertion_id,
            PreconstructionScopeAssertion.project_id == project_id,
        )
        .first()
    )
    if assertion is None:
        raise _not_found("Scope assertion not found")
    return assertion


def list_assertions(
    db: Session,
    project_id: int,
    review_set_id: int,
    *,
    limit: int,
    offset: int,
    review_status: str | None = None,
    concept_code: str | None = None,
    category: str | None = None,
    assertion_type: str | None = None,
    source_id: int | None = None,
    document_role: str | None = None,
    discipline: str | None = None,
    trade: str | None = None,
    inclusion_state: str | None = None,
    origin: str | None = None,
    confidence_min: float | None = None,
    confidence_max: float | None = None,
    search: str = "",
    assertion_set_id: int | None = None,
    current_assertion_set_only: bool = False,
) -> tuple[list[PreconstructionScopeAssertion], int]:
    """Bounded, allowlisted filtering with deterministic ordering.

    Ordering is review priority, then concept code (whose ``category.name``
    form groups concepts by category), then source, then assertion id.
    """
    query = db.query(PreconstructionScopeAssertion).filter(
        PreconstructionScopeAssertion.project_id == project_id,
        PreconstructionScopeAssertion.review_set_id == review_set_id,
    )
    if assertion_set_id is not None:
        query = query.filter(
            PreconstructionScopeAssertion.assertion_set_id == assertion_set_id
        )
    elif current_assertion_set_only:
        current_id = latest_assertion_set_id(db, project_id, review_set_id)
        # Manual assertions have no assertion set and remain visible.
        query = query.filter(
            (PreconstructionScopeAssertion.assertion_set_id == current_id)
            | (PreconstructionScopeAssertion.assertion_set_id.is_(None))
        )
    if review_status is not None:
        query = query.filter(PreconstructionScopeAssertion.status == review_status)
    if concept_code is not None:
        query = query.filter(
            PreconstructionScopeAssertion.concept_code == concept_code
        )
    if category is not None:
        query = query.filter(
            PreconstructionScopeAssertion.concept_code.startswith(f"{category}.")
        )
    if assertion_type is not None:
        query = query.filter(
            PreconstructionScopeAssertion.assertion_type == assertion_type
        )
    if source_id is not None:
        query = query.filter(PreconstructionScopeAssertion.source_id == source_id)
    if origin is not None:
        query = query.filter(PreconstructionScopeAssertion.origin == origin)
    if inclusion_state is not None:
        query = query.filter(
            PreconstructionScopeAssertion.inclusion_state == inclusion_state
        )
    if discipline:
        query = query.filter(PreconstructionScopeAssertion.discipline == discipline)
    if trade:
        query = query.filter(PreconstructionScopeAssertion.trade == trade)
    if confidence_min is not None:
        query = query.filter(
            PreconstructionScopeAssertion.confidence >= Decimal(str(confidence_min))
        )
    if confidence_max is not None:
        query = query.filter(
            PreconstructionScopeAssertion.confidence <= Decimal(str(confidence_max))
        )
    if document_role is not None:
        query = query.join(
            PreconstructionReviewSource,
            PreconstructionReviewSource.id == PreconstructionScopeAssertion.source_id,
        ).filter(PreconstructionReviewSource.document_role == document_role)
    normalized_search = normalized_comparison_text(search)
    if normalized_search:
        # Bounded metadata search only: never full content-segment search.
        pattern = f"%{normalized_search}%"
        query = query.filter(
            func.lower(PreconstructionScopeAssertion.subject).like(pattern)
            | PreconstructionScopeAssertion.normalized_requirement.like(pattern)
            | func.lower(PreconstructionScopeAssertion.concept_code).like(pattern)
        )

    total = query.with_entities(func.count(PreconstructionScopeAssertion.id)).scalar()
    status_rank = case(
        *[
            (PreconstructionScopeAssertion.status == key, value)
            for key, value in _STATUS_ORDER.items()
        ],
        else_=99,
    )
    items = (
        query.order_by(
            status_rank.asc(),
            PreconstructionScopeAssertion.concept_code.asc(),
            PreconstructionScopeAssertion.source_id.asc(),
            PreconstructionScopeAssertion.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def _source_summary(source: PreconstructionReviewSource | None) -> dict | None:
    if source is None:
        return None
    return {
        "id": source.id,
        "display_name": source.display_name_snapshot,
        "document_role": source.document_role,
        "source_type": source.source_type,
        "document_id": source.document_id,
        "drawing_revision_id": source.drawing_revision_id,
        "sheet_number": source.sheet_number_snapshot,
        "revision_code": source.revision_code_snapshot,
        "discipline": source.discipline,
        "trade": source.trade,
    }


def _evidence_summary(
    evidence: PreconstructionAssertionEvidence,
    source: PreconstructionReviewSource | None,
    review_set_id: int,
    sheet_id_by_revision: dict[int, int],
) -> dict:
    project_id = evidence.project_id
    revision_id = source.drawing_revision_id if source else None
    sheet_id = sheet_id_by_revision.get(revision_id) if revision_id else None
    viewer_target = (
        {
            "page": "drawingViewer",
            "projectId": project_id,
            "sheetId": sheet_id,
            "revisionId": revision_id,
        }
        if revision_id and sheet_id
        else {
            "page": "projectDocuments",
            "projectId": project_id,
            "documentId": source.document_id if source else None,
        }
    )
    return {
        "id": evidence.id,
        "source_id": evidence.source_id,
        "source_display_name": source.display_name_snapshot if source else None,
        "document_role": source.document_role if source else None,
        "sheet_number": source.sheet_number_snapshot if source else None,
        "revision_code": source.revision_code_snapshot if source else None,
        "snapshot_id": evidence.content_snapshot_id,
        "page_number": evidence.page_number,
        "segment_index": evidence.segment_index,
        "excerpt": evidence.excerpt,
        "evidence_role": evidence.evidence_role,
        "evidence_role_label": EVIDENCE_ROLES[evidence.evidence_role],
        "text_hash": evidence.text_hash[:16],
        "viewer_target": viewer_target,
        "content_target": {
            "page": "projectPreconstruction",
            "projectId": project_id,
            "reviewSetId": review_set_id,
            "sourceId": evidence.source_id,
            "snapshotId": evidence.content_snapshot_id,
            "pageNumber": evidence.page_number,
        },
    }


def assertion_payloads(
    db: Session,
    project_id: int,
    assertions: list[PreconstructionScopeAssertion],
    *,
    include_evidence: bool = True,
    evidence_limit: int = 20,
) -> list[dict]:
    """Batch-resolve sources, evidence, and current reviews for a page.

    Query budget is fixed regardless of page size: one source query, one
    evidence query, one drawing-sheet query, and one latest-review query.
    Concept metadata comes from constants and costs no query.
    """
    if not assertions:
        return []
    assertion_ids = [item.id for item in assertions]
    source_ids = sorted({item.source_id for item in assertions})
    sources = {
        source.id: source
        for source in db.query(PreconstructionReviewSource)
        .filter(
            PreconstructionReviewSource.project_id == project_id,
            PreconstructionReviewSource.id.in_(source_ids),
        )
        .all()
    }

    evidence_by_assertion: dict[int, list[PreconstructionAssertionEvidence]] = {}
    sheet_id_by_revision: dict[int, int] = {}
    if include_evidence:
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
        for row in rows:
            evidence_by_assertion.setdefault(row.assertion_id, []).append(row)
        revision_ids = sorted(
            {
                source.drawing_revision_id
                for source in sources.values()
                if source.drawing_revision_id
            }
        )
        if revision_ids:
            sheet_id_by_revision = {
                revision_id: sheet_id
                for revision_id, sheet_id in db.execute(
                    select(
                        DrawingRevision.id, DrawingRevision.drawing_sheet_id
                    ).where(
                        DrawingRevision.project_id == project_id,
                        DrawingRevision.id.in_(revision_ids),
                    )
                ).all()
            }

    latest_review_ids = (
        select(func.max(PreconstructionAssertionReview.id))
        .where(PreconstructionAssertionReview.assertion_id.in_(assertion_ids))
        .group_by(PreconstructionAssertionReview.assertion_id)
    )
    latest_reviews = {
        review.assertion_id: review
        for review in db.query(PreconstructionAssertionReview)
        .filter(PreconstructionAssertionReview.id.in_(latest_review_ids))
        .all()
    }

    payloads = []
    for assertion in assertions:
        concept = taxonomy.resolve_concept(assertion.concept_code)
        review = latest_reviews.get(assertion.id)
        evidence = evidence_by_assertion.get(assertion.id, [])
        source = sources.get(assertion.source_id)
        payloads.append(
            {
                "id": assertion.id,
                "assertion_set_id": assertion.assertion_set_id,
                "review_set_id": assertion.review_set_id,
                "origin": assertion.origin,
                "origin_label": ASSERTION_ORIGINS[assertion.origin],
                "concept_code": assertion.concept_code,
                "concept_name": concept.name if concept else assertion.concept_code,
                "concept_category": concept.category if concept else None,
                "concept_category_label": (
                    taxonomy.CATEGORY_LABELS[concept.category] if concept else None
                ),
                "concept_scope_kind": concept.scope_kind if concept else None,
                "concept_status": concept.status if concept else "unknown",
                "taxonomy_version": assertion.taxonomy_version,
                "assertion_type": assertion.assertion_type,
                "assertion_type_label": ASSERTION_TYPES[assertion.assertion_type],
                "subject": assertion.subject,
                "requirement_text": assertion.requirement_text,
                "responsibility_party": assertion.responsibility_party,
                "discipline": assertion.discipline,
                "trade": assertion.trade,
                "specification_section": assertion.specification_section,
                "drawing_sheet": assertion.drawing_sheet,
                "quantity_value": (
                    float(assertion.quantity_value)
                    if assertion.quantity_value is not None
                    else None
                ),
                "quantity_unit": assertion.quantity_unit,
                "location_text": assertion.location_text,
                "inclusion_state": assertion.inclusion_state,
                "inclusion_state_label": INCLUSION_STATES[assertion.inclusion_state],
                "confidence": (
                    float(assertion.confidence)
                    if assertion.confidence is not None
                    else None
                ),
                "confidence_basis": assertion.confidence_basis,
                "status": assertion.status,
                "status_label": assertion_status_label(assertion.status),
                "review_decision": review.decision if review else None,
                "review_reason_code": review.reason_code if review else None,
                "review_reason_label": (
                    review_reason_label(review.reason_code) if review else None
                ),
                "reviewer_note": review.reviewer_note if review else None,
                "reviewed_by": review.reviewed_by if review else None,
                "reviewed_at": review.reviewed_at if review else None,
                "supersedes_assertion_id": assertion.supersedes_assertion_id,
                "created_at": assertion.created_at,
                "evidence_count": len(evidence),
                "evidence": [
                    _evidence_summary(
                        item, source, assertion.review_set_id, sheet_id_by_revision
                    )
                    for item in evidence[:evidence_limit]
                ],
                "evidence_truncated": len(evidence) > evidence_limit,
                "source": _source_summary(source),
            }
        )
    return payloads


def assertion_summary_counts(
    db: Session, project_id: int, review_set_id: int
) -> dict:
    rows = (
        db.query(
            PreconstructionScopeAssertion.status,
            func.count(PreconstructionScopeAssertion.id),
        )
        .filter(
            PreconstructionScopeAssertion.project_id == project_id,
            PreconstructionScopeAssertion.review_set_id == review_set_id,
        )
        .group_by(PreconstructionScopeAssertion.status)
        .all()
    )
    counts = {key: 0 for key in ASSERTION_STATUSES}
    for value, count in rows:
        counts[value] = count
    manual = (
        db.query(func.count(PreconstructionScopeAssertion.id))
        .filter(
            PreconstructionScopeAssertion.project_id == project_id,
            PreconstructionScopeAssertion.review_set_id == review_set_id,
            PreconstructionScopeAssertion.origin == "manual",
        )
        .scalar()
    )
    return {
        "total": sum(counts.values()),
        "proposed": counts["proposed"],
        "accepted": counts["accepted"],
        "rejected": counts["rejected"],
        "needs_review": counts["needs_review"],
        "superseded": counts["superseded"],
        "manual": manual,
    }


def list_assertion_reviews(
    db: Session, project_id: int, assertion_id: int
) -> list[dict]:
    reviews = (
        db.query(PreconstructionAssertionReview)
        .filter(
            PreconstructionAssertionReview.project_id == project_id,
            PreconstructionAssertionReview.assertion_id == assertion_id,
        )
        .order_by(
            PreconstructionAssertionReview.reviewed_at.asc(),
            PreconstructionAssertionReview.id.asc(),
        )
        .all()
    )
    return [
        {
            "id": review.id,
            "decision": review.decision,
            "decision_label": ASSERTION_STATUSES[DECISION_TO_STATUS[review.decision]],
            "reason_code": review.reason_code,
            "reason_label": review_reason_label(review.reason_code),
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

def _require_reviewable(review_set: PreconstructionReviewSet) -> None:
    if review_set.status == "archived":
        raise _conflict("Archived preconstruction review sets are read-only")


def review_assertion(
    db: Session,
    review_set: PreconstructionReviewSet,
    assertion: PreconstructionScopeAssertion,
    reviewer_id: int,
    *,
    decision: str,
    reason_code: str | None,
    reviewer_note: str | None,
    config: PreconstructionScopeConfig,
) -> PreconstructionAssertionReview:
    """Append one review event and move the server-controlled status.

    History is append-only: prior decisions are never updated or deleted.
    """
    _require_reviewable(review_set)
    if assertion.status == "superseded":
        raise _conflict("Superseded assertions cannot be reviewed")
    if not transition_allowed(assertion.status, decision):
        raise _conflict(
            f"Cannot move a {assertion.status} assertion to {decision}"
        )
    note = sanitize_text(reviewer_note)
    if note and len(note) > config.max_reviewer_note_characters:
        raise _unprocessable("Reviewer note exceeds the configured limit")
    if note_required(assertion.status, decision, reason_code) and not note:
        raise _unprocessable(
            "A reviewer note is required for this decision"
        )

    previous = (
        db.query(PreconstructionAssertionReview)
        .filter(PreconstructionAssertionReview.assertion_id == assertion.id)
        .order_by(PreconstructionAssertionReview.id.desc())
        .first()
    )
    review = PreconstructionAssertionReview(
        project_id=assertion.project_id,
        assertion_id=assertion.id,
        decision=decision,
        reason_code=reason_code,
        reviewer_note=note,
        reviewed_by=reviewer_id,
        reviewed_at=utc_now(),
        previous_review_id=previous.id if previous else None,
    )
    db.add(review)
    assertion.status = DECISION_TO_STATUS[decision]
    db.commit()
    db.refresh(review)
    return review


def create_manual_assertion(
    db: Session,
    review_set: PreconstructionReviewSet,
    source: PreconstructionReviewSource,
    author_id: int,
    payload,
    config: PreconstructionScopeConfig,
) -> PreconstructionScopeAssertion:
    """Create one human-authored assertion with server-derived excerpts.

    Manual assertions carry ``origin='manual'`` and no confidence. They are
    never presented as model output.
    """
    _require_reviewable(review_set)
    concept = taxonomy.resolve_concept(payload.concept_code)
    if concept is None or concept.status != "active":
        raise _unprocessable("Unknown scope concept code")

    existing_manual = (
        db.query(func.count(PreconstructionScopeAssertion.id))
        .filter(
            PreconstructionScopeAssertion.project_id == review_set.project_id,
            PreconstructionScopeAssertion.review_set_id == review_set.id,
            PreconstructionScopeAssertion.origin == "manual",
        )
        .scalar()
    )
    if existing_manual >= config.max_manual_assertions_per_review_set:
        raise _conflict("Manual assertion limit reached for this review set")

    segment_ids = sorted(set(payload.evidence_segment_ids))
    if len(segment_ids) > config.max_evidence_per_assertion:
        raise _unprocessable("Too many evidence segments selected")

    # Evidence must come from a completed snapshot belonging to this source.
    rows = (
        db.query(
            PreconstructionContentSegment,
            PreconstructionContentSnapshot.review_source_id,
        )
        .join(
            PreconstructionContentSnapshot,
            PreconstructionContentSnapshot.id
            == PreconstructionContentSegment.snapshot_id,
        )
        .filter(
            PreconstructionContentSegment.project_id == review_set.project_id,
            PreconstructionContentSegment.id.in_(segment_ids),
            PreconstructionContentSnapshot.review_source_id == source.id,
            PreconstructionContentSnapshot.status.in_(
                ("completed", "completed_with_warnings")
            ),
        )
        .all()
    )
    if len(rows) != len(segment_ids):
        raise _unprocessable(
            "Selected evidence does not belong to this source's prepared content"
        )

    page_numbers = {
        page_id: page_number
        for page_id, page_number in db.execute(
            select(
                PreconstructionContentPage.id, PreconstructionContentPage.page_number
            ).where(
                PreconstructionContentPage.project_id == review_set.project_id,
                PreconstructionContentPage.id.in_(
                    sorted({segment.page_id for segment, _ in rows})
                ),
            )
        ).all()
    }

    subject = sanitize_text(payload.subject)
    if not subject:
        raise _unprocessable("Subject is required")
    requirement = sanitize_text(payload.requirement_text)
    quantity_value = _decimal(payload.quantity_value)
    quantity_unit = taxonomy.normalize_unit(payload.quantity_unit)
    if quantity_value is None:
        quantity_unit = None

    now = utc_now()
    assertion = PreconstructionScopeAssertion(
        project_id=review_set.project_id,
        assertion_set_id=None,
        review_set_id=review_set.id,
        source_id=source.id,
        origin="manual",
        concept_code=concept.code,
        taxonomy_version=taxonomy.TAXONOMY_VERSION,
        assertion_type=payload.assertion_type,
        subject=subject,
        requirement_text=requirement,
        normalized_requirement=normalized_comparison_text(requirement) or None,
        responsibility_party=sanitize_text(payload.responsibility_party),
        discipline=sanitize_text(payload.discipline),
        trade=sanitize_text(payload.trade),
        specification_section=sanitize_text(payload.specification_section),
        drawing_sheet=sanitize_text(payload.drawing_sheet),
        quantity_value=quantity_value,
        quantity_unit=quantity_unit,
        location_text=sanitize_text(payload.location_text),
        inclusion_state=payload.inclusion_state,
        confidence=None,
        confidence_basis=None,
        provider_assertion_key=None,
        status="accepted",
        created_by=author_id,
        created_at=now,
    )
    db.add(assertion)
    db.flush()

    evidence_rows = []
    for segment, _ in sorted(rows, key=lambda entry: entry[0].id):
        excerpt = sanitize_text(segment.text[: config.evidence_excerpt_characters])
        if not excerpt:
            raise _unprocessable("Selected evidence resolved to empty text")
        evidence_rows.append(
            {
                "project_id": review_set.project_id,
                "assertion_id": assertion.id,
                "source_id": source.id,
                "content_snapshot_id": segment.snapshot_id,
                "content_page_id": segment.page_id,
                "content_segment_id": segment.id,
                "page_number": page_numbers[segment.page_id],
                "segment_index": segment.segment_index,
                "text_hash": segment.text_hash,
                "excerpt": excerpt,
                "character_start": segment.character_start,
                "character_end": segment.character_end,
                "evidence_role": "primary",
                "created_at": now,
            }
        )
    db.execute(insert(PreconstructionAssertionEvidence), evidence_rows)

    note = sanitize_text(payload.reviewer_note)
    db.add(
        PreconstructionAssertionReview(
            project_id=review_set.project_id,
            assertion_id=assertion.id,
            decision="accepted",
            reason_code=None,
            reviewer_note=note or "Human-authored assertion",
            reviewed_by=author_id,
            reviewed_at=now,
            previous_review_id=None,
        )
    )
    db.commit()
    db.refresh(assertion)
    return assertion


def supersede_assertion(
    db: Session,
    review_set: PreconstructionReviewSet,
    assertion: PreconstructionScopeAssertion,
    replacement: PreconstructionScopeAssertion,
    reviewer_id: int,
    *,
    reviewer_note: str | None,
    config: PreconstructionScopeConfig,
) -> PreconstructionScopeAssertion:
    """Explicit human-marked replacement. Never inferred automatically."""
    _require_reviewable(review_set)
    if assertion.id == replacement.id:
        raise _unprocessable("An assertion cannot supersede itself")
    if assertion.review_set_id != replacement.review_set_id:
        raise _unprocessable("Superseding assertions must share a review set")
    if assertion.status == "superseded":
        raise _conflict("Assertion is already superseded")
    note = sanitize_text(reviewer_note)
    if not note:
        raise _unprocessable("A reviewer note is required to supersede an assertion")
    if len(note) > config.max_reviewer_note_characters:
        raise _unprocessable("Reviewer note exceeds the configured limit")

    previous = (
        db.query(PreconstructionAssertionReview)
        .filter(PreconstructionAssertionReview.assertion_id == assertion.id)
        .order_by(PreconstructionAssertionReview.id.desc())
        .first()
    )
    db.add(
        PreconstructionAssertionReview(
            project_id=assertion.project_id,
            assertion_id=assertion.id,
            decision="rejected",
            reason_code="source_superseded",
            reviewer_note=note,
            reviewed_by=reviewer_id,
            reviewed_at=utc_now(),
            previous_review_id=previous.id if previous else None,
        )
    )
    assertion.status = "superseded"
    replacement.supersedes_assertion_id = assertion.id
    db.commit()
    db.refresh(assertion)
    return assertion
