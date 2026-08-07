"""Human-initiated follow-up actions raised from accepted scope findings.

A follow-up is an intent plus a link. A person decides to act on a finding a
person already accepted, edits a deterministic draft, creates the record
through that record's own existing workflow, and links it back here.

This module never creates, approves, or mutates an RFI, Change Order,
Submittal, Task, relationship, procurement record, or notification. It never
touches an assertion, an evidence row, a finding, a finding set, or a
comparison manifest. It calls no AI provider and adds no analysis type.

The finding's own append-only review history remains the sole authority on
whether a finding is valid; a follow-up carries a lifecycle, never a second
review decision.
"""

from datetime import datetime, timezone
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import PreconstructionFollowUpConfig
from app.models.preconstruction import (
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)
from app.models.scope_assertion import PreconstructionScopeAssertion
from app.models.scope_comparison import (
    PreconstructionComparisonPlan,
    PreconstructionFinding,
    PreconstructionFindingAssertion,
    PreconstructionFindingEvidence,
    PreconstructionFindingReview,
)
from app.models.scope_follow_up import PreconstructionFindingFollowUp
from app.preconstruction.comparison import (
    FINDING_SEVERITIES,
    FINDING_STATUSES,
    FINDING_TYPES,
    resolve_comparison_type,
)
from app.preconstruction.follow_up import (
    ACTIVE_FOLLOW_UP_STATUSES,
    FOLLOW_UP_ACTIONS,
    FOLLOW_UP_ACTION_BY_VALUE,
    FOLLOW_UP_ELIGIBLE_FINDING_STATUSES,
    FOLLOW_UP_STATUSES,
    FOLLOW_UP_TEMPLATE_VERSION,
    DraftContext,
    action_payload,
    build_draft_body,
    build_draft_title,
    closure_note_required,
    follow_up_transition_allowed,
    target_required,
)
from app.services.preconstruction_scope import sanitize_text
from app.services.relationship_resolver import (
    resolve_entity_summaries,
    resolve_relationship_entity,
)


_FOLLOW_UP_STATUS_ORDER = {
    "planned": 0,
    "linked": 1,
    "completed": 2,
    "cancelled": 3,
}

MAX_DRAFT_SUBJECT_CHARACTERS = 160
MAX_DRAFT_SUMMARY_CHARACTERS = 400
MAX_DRAFT_CITATION_CHARACTERS = 160


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


def _clip(value: str | None, limit: int) -> str | None:
    """Sanitize then hard-bound one single-line fragment destined for a draft."""
    normalized = sanitize_text(value)
    if not normalized:
        return None
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _clip_multiline(value: str | None, limit: int) -> str | None:
    """Bound an edited draft body while preserving its line structure.

    ``sanitize_text`` collapses every run of whitespace, which is right for a
    subject or a citation and wrong for a body a person has laid out. This
    applies the same character safety rules line by line: NFKC, no control or
    format characters, no trailing spaces, and at most one blank line in a row.
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
    lines: list[str] = []
    for raw_line in cleaned.split("\n"):
        line = " ".join(raw_line.split())
        if not line and lines and not lines[-1]:
            continue
        lines.append(line)
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    collapsed = "\n".join(lines)
    if not collapsed:
        return None
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# Lookups and gates
# ---------------------------------------------------------------------------

def get_follow_up(
    db: Session, project_id: int, follow_up_id: int
) -> PreconstructionFindingFollowUp:
    follow_up = (
        db.query(PreconstructionFindingFollowUp)
        .filter(
            PreconstructionFindingFollowUp.id == follow_up_id,
            PreconstructionFindingFollowUp.project_id == project_id,
        )
        .first()
    )
    if follow_up is None:
        raise _not_found("Follow-up not found")
    return follow_up


def _require_writable(
    plan: PreconstructionComparisonPlan, review_set: PreconstructionReviewSet
) -> None:
    if plan.status == "archived" or review_set.status == "archived":
        raise _conflict("Archived comparison plans are read-only")


def require_actionable_finding(finding: PreconstructionFinding) -> None:
    """Only an accepted finding may raise new work.

    ``intentional_exclusion`` is refused on purpose: it is the recorded human
    decision *not* to act, so raising work from it would contradict a
    judgement a person already made.
    """
    if finding.status not in FOLLOW_UP_ELIGIBLE_FINDING_STATUSES:
        raise _conflict(
            "Only an accepted finding can raise a follow-up; this finding is "
            f"{FINDING_STATUSES.get(finding.status, finding.status)}"
        )


def latest_acceptance_review_id(db: Session, finding_id: int) -> int | None:
    """The exact acceptance that authorizes the follow-up, pinned at creation."""
    row = (
        db.query(PreconstructionFindingReview.id)
        .filter(
            PreconstructionFindingReview.finding_id == finding_id,
            PreconstructionFindingReview.decision == "accepted",
        )
        .order_by(PreconstructionFindingReview.id.desc())
        .first()
    )
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Deterministic draft assembly
# ---------------------------------------------------------------------------

def _draft_context(
    db: Session,
    project_id: int,
    finding: PreconstructionFinding,
    plan: PreconstructionComparisonPlan,
    action_type: str,
) -> DraftContext:
    """Assemble the draft inputs from stored finding data only.

    Nothing is invented here and no client text is used. Provider-authored
    summaries are treated exactly like evidence excerpts: sanitized, bounded,
    plain text.
    """
    links = (
        db.query(PreconstructionFindingAssertion)
        .filter(
            PreconstructionFindingAssertion.project_id == project_id,
            PreconstructionFindingAssertion.finding_id == finding.id,
        )
        .order_by(
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

    requirement_subjects: list[str] = []
    coverage_subjects: list[str] = []
    for link in links:
        assertion = assertions.get(link.assertion_id)
        if assertion is None:
            continue
        subject = _clip(assertion.subject, MAX_DRAFT_SUBJECT_CHARACTERS)
        if not subject:
            continue
        if link.side in ("requirement", "prior_revision"):
            if subject not in requirement_subjects:
                requirement_subjects.append(subject)
        elif link.side in ("coverage", "current_revision"):
            if subject not in coverage_subjects:
                coverage_subjects.append(subject)

    evidence_rows = (
        db.query(PreconstructionFindingEvidence)
        .filter(
            PreconstructionFindingEvidence.project_id == project_id,
            PreconstructionFindingEvidence.finding_id == finding.id,
        )
        .order_by(
            PreconstructionFindingEvidence.page_number.asc(),
            PreconstructionFindingEvidence.segment_index.asc(),
            PreconstructionFindingEvidence.id.asc(),
        )
        .all()
    )
    source_ids = sorted({row.source_id for row in evidence_rows})
    sources = {
        row.id: row
        for row in db.query(PreconstructionReviewSource)
        .filter(
            PreconstructionReviewSource.project_id == project_id,
            PreconstructionReviewSource.id.in_(source_ids),
        )
        .all()
    } if source_ids else {}

    citations: list[str] = []
    for row in evidence_rows:
        source = sources.get(row.source_id)
        name = source.display_name_snapshot if source else "Review source"
        citation = _clip(
            f"{name} — page {row.page_number}, segment {row.segment_index}",
            MAX_DRAFT_CITATION_CHARACTERS,
        )
        if citation and citation not in citations:
            citations.append(citation)

    comparison_type = resolve_comparison_type(plan.comparison_type)
    return DraftContext(
        action_type=action_type,
        finding_type_label=FINDING_TYPES.get(finding.finding_type, finding.finding_type),
        severity_label=FINDING_SEVERITIES.get(finding.severity, finding.severity),
        comparison_type_label=(
            comparison_type.label if comparison_type else plan.comparison_type
        ),
        finding_title=_clip(finding.title, MAX_DRAFT_SUBJECT_CHARACTERS) or "Finding",
        finding_summary=_clip(finding.summary, MAX_DRAFT_SUMMARY_CHARACTERS),
        requirement_subjects=tuple(requirement_subjects),
        coverage_subjects=tuple(coverage_subjects),
        evidence_citations=tuple(citations),
    )


def build_follow_up_draft(
    db: Session,
    project_id: int,
    finding: PreconstructionFinding,
    plan: PreconstructionComparisonPlan,
    action_type: str,
    config: PreconstructionFollowUpConfig,
) -> dict:
    """Deterministic draft for one action. Same finding in, same draft out."""
    action = FOLLOW_UP_ACTION_BY_VALUE.get(action_type)
    if action is None:
        raise _unprocessable("Unknown follow-up action")
    context = _draft_context(db, project_id, finding, plan, action_type)
    return {
        "action_type": action.value,
        "action_label": action.label,
        "action_guidance": action.guidance,
        "target_type": action.target_type,
        "draft_title": build_draft_title(context)[: config.max_draft_title_characters],
        "draft_body": build_draft_body(context)[: config.max_draft_body_characters],
        "draft_template_version": FOLLOW_UP_TEMPLATE_VERSION,
    }


def follow_up_action_catalog() -> list[dict]:
    return [action_payload(item) for item in FOLLOW_UP_ACTIONS]


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def follow_up_payloads(
    db: Session,
    project_id: int,
    follow_ups: list[PreconstructionFindingFollowUp],
) -> list[dict]:
    """Batch-resolve findings and link targets for a page.

    Query budget is fixed regardless of page size: one finding query and one
    grouped target-resolution pass. There is no per-row query.
    """
    if not follow_ups:
        return []
    finding_ids = sorted({item.finding_id for item in follow_ups})
    findings = {
        row.id: row
        for row in db.query(PreconstructionFinding)
        .filter(
            PreconstructionFinding.project_id == project_id,
            PreconstructionFinding.id.in_(finding_ids),
        )
        .all()
    }
    references = {
        (item.target_type, item.target_id)
        for item in follow_ups
        if item.target_type and item.target_id
    }
    targets = (
        resolve_entity_summaries(db, project_id, references) if references else {}
    )

    payloads = []
    for item in follow_ups:
        action = FOLLOW_UP_ACTION_BY_VALUE.get(item.action_type)
        finding = findings.get(item.finding_id)
        finding_status = finding.status if finding else "superseded"
        target = targets.get((item.target_type, item.target_id))
        is_open = item.status in ACTIVE_FOLLOW_UP_STATUSES
        payloads.append(
            {
                "id": item.id,
                "project_id": item.project_id,
                "review_set_id": item.review_set_id,
                "comparison_plan_id": item.comparison_plan_id,
                "finding_id": item.finding_id,
                "finding_review_id": item.finding_review_id,
                "action_type": item.action_type,
                "action_label": action.label if action else item.action_type,
                "action_guidance": action.guidance if action else "",
                "status": item.status,
                "status_label": FOLLOW_UP_STATUSES.get(item.status, item.status),
                "target_type": item.target_type,
                "target_id": item.target_id,
                "target": target.response() if target else None,
                "draft_title": item.draft_title,
                "draft_body": item.draft_body,
                "draft_template_version": item.draft_template_version,
                "closure_note": item.closure_note,
                "finding_status": finding_status,
                "finding_status_label": FINDING_STATUSES.get(
                    finding_status, finding_status
                ),
                # Derived, never stored. A reversed review is surfaced, not
                # applied: the follow-up row itself is never rewritten.
                "finding_no_longer_accepted": (
                    finding_status not in FOLLOW_UP_ELIGIBLE_FINDING_STATUSES
                ),
                "can_edit_draft": item.status == "planned",
                "can_link": (
                    item.status == "planned" and target_required(item.action_type)
                ),
                "can_close": is_open,
                "created_by": item.created_by,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "linked_by": item.linked_by,
                "linked_at": item.linked_at,
                "closed_by": item.closed_by,
                "closed_at": item.closed_at,
            }
        )
    return payloads


def list_follow_ups_for_finding(
    db: Session, project_id: int, finding_id: int
) -> list[PreconstructionFindingFollowUp]:
    return (
        db.query(PreconstructionFindingFollowUp)
        .filter(
            PreconstructionFindingFollowUp.project_id == project_id,
            PreconstructionFindingFollowUp.finding_id == finding_id,
        )
        .order_by(
            PreconstructionFindingFollowUp.id.asc(),
        )
        .all()
    )


def list_follow_ups(
    db: Session,
    project_id: int,
    plan_id: int,
    *,
    limit: int,
    offset: int,
    action_type: str | None = None,
    follow_up_status: str | None = None,
    target_type: str | None = None,
    finding_id: int | None = None,
) -> tuple[list[PreconstructionFindingFollowUp], int]:
    query = db.query(PreconstructionFindingFollowUp).filter(
        PreconstructionFindingFollowUp.project_id == project_id,
        PreconstructionFindingFollowUp.comparison_plan_id == plan_id,
    )
    if action_type:
        query = query.filter(
            PreconstructionFindingFollowUp.action_type == action_type
        )
    if follow_up_status:
        query = query.filter(
            PreconstructionFindingFollowUp.status == follow_up_status
        )
    if target_type:
        query = query.filter(
            PreconstructionFindingFollowUp.target_type == target_type
        )
    if finding_id:
        query = query.filter(
            PreconstructionFindingFollowUp.finding_id == finding_id
        )
    total = query.with_entities(
        func.count(PreconstructionFindingFollowUp.id)
    ).scalar()
    items = (
        query.order_by(
            PreconstructionFindingFollowUp.status.asc(),
            PreconstructionFindingFollowUp.action_type.asc(),
            PreconstructionFindingFollowUp.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Status ordering is planned first, then linked, completed, cancelled.
    # SQL sorts alphabetically, so the deterministic priority is applied here
    # over the already-bounded page.
    items.sort(
        key=lambda row: (
            _FOLLOW_UP_STATUS_ORDER.get(row.status, 99),
            row.action_type,
            row.id,
        )
    )
    return items, total


def follow_up_summary_counts(db: Session, project_id: int, plan_id: int) -> dict:
    rows = (
        db.query(
            PreconstructionFindingFollowUp.status,
            func.count(PreconstructionFindingFollowUp.id),
        )
        .filter(
            PreconstructionFindingFollowUp.project_id == project_id,
            PreconstructionFindingFollowUp.comparison_plan_id == plan_id,
        )
        .group_by(PreconstructionFindingFollowUp.status)
        .all()
    )
    counts = {value: 0 for value in FOLLOW_UP_STATUSES}
    for value, count in rows:
        counts[value] = count
    counts["total"] = sum(counts[value] for value in FOLLOW_UP_STATUSES)
    return counts


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def create_follow_up(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    finding: PreconstructionFinding,
    author_id: int,
    payload,
    config: PreconstructionFollowUpConfig,
) -> PreconstructionFindingFollowUp:
    """Raise one planned follow-up from an accepted finding.

    Creates no authoritative record. The human still creates the RFI, Change
    Order, or Submittal through that record's own workflow and links it back.
    """
    _require_writable(plan, review_set)
    require_actionable_finding(finding)
    action = FOLLOW_UP_ACTION_BY_VALUE.get(payload.action_type)
    if action is None:
        raise _unprocessable("Unknown follow-up action")

    per_finding = (
        db.query(func.count(PreconstructionFindingFollowUp.id))
        .filter(
            PreconstructionFindingFollowUp.project_id == plan.project_id,
            PreconstructionFindingFollowUp.finding_id == finding.id,
        )
        .scalar()
    )
    if per_finding >= config.max_follow_ups_per_finding:
        raise _conflict("Follow-up limit reached for this finding")
    per_plan = (
        db.query(func.count(PreconstructionFindingFollowUp.id))
        .filter(
            PreconstructionFindingFollowUp.project_id == plan.project_id,
            PreconstructionFindingFollowUp.comparison_plan_id == plan.id,
        )
        .scalar()
    )
    if per_plan >= config.max_follow_ups_per_plan:
        raise _conflict("Follow-up limit reached for this comparison plan")

    draft = build_follow_up_draft(
        db, plan.project_id, finding, plan, payload.action_type, config
    )
    title = _clip(payload.draft_title, config.max_draft_title_characters) or draft[
        "draft_title"
    ]
    body = _clip_multiline(
        payload.draft_body, config.max_draft_body_characters
    ) or draft["draft_body"]

    now = utc_now()
    follow_up = PreconstructionFindingFollowUp(
        project_id=plan.project_id,
        finding_id=finding.id,
        review_set_id=finding.review_set_id,
        comparison_plan_id=plan.id,
        finding_review_id=latest_acceptance_review_id(db, finding.id),
        action_type=action.value,
        status="planned",
        target_type=None,
        target_id=None,
        draft_title=title,
        draft_body=body,
        draft_template_version=FOLLOW_UP_TEMPLATE_VERSION,
        created_by=author_id,
        created_at=now,
        updated_at=now,
    )
    db.add(follow_up)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict(
            "An active follow-up of this type already exists for this finding"
        ) from error
    db.refresh(follow_up)
    return follow_up


def update_follow_up(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    follow_up: PreconstructionFindingFollowUp,
    payload,
    config: PreconstructionFollowUpConfig,
) -> PreconstructionFindingFollowUp:
    """Edit the draft while the follow-up is still planned."""
    _require_writable(plan, review_set)
    if follow_up.status != "planned":
        raise _conflict("Only a planned follow-up draft can be edited")

    fields = payload.model_fields_set
    if "draft_title" in fields:
        title = _clip(payload.draft_title, config.max_draft_title_characters)
        if not title:
            raise _unprocessable("A draft title is required")
        follow_up.draft_title = title
    if "draft_body" in fields:
        body = _clip_multiline(payload.draft_body, config.max_draft_body_characters)
        if not body:
            raise _unprocessable("A draft body is required")
        follow_up.draft_body = body
    follow_up.updated_at = utc_now()
    db.commit()
    db.refresh(follow_up)
    return follow_up


def link_follow_up(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    follow_up: PreconstructionFindingFollowUp,
    user_id: int,
    payload,
) -> PreconstructionFindingFollowUp:
    """Attach a record the human already created through its own workflow.

    The target is resolved through the existing relationship entity resolver,
    so ownership, existence, and selectability are enforced by the same code
    that guards the relationship graph. Nothing is created here.
    """
    _require_writable(plan, review_set)
    if not follow_up_transition_allowed(follow_up.status, "linked"):
        raise _conflict(f"A {follow_up.status} follow-up cannot be linked")
    action = FOLLOW_UP_ACTION_BY_VALUE.get(follow_up.action_type)
    if action is None or action.target_type is None:
        raise _unprocessable("This follow-up action has no linkable record type")
    if payload.target_type != action.target_type:
        raise _unprocessable(
            f"A {action.label} follow-up links to a {action.target_type} record"
        )

    resolve_relationship_entity(
        db,
        follow_up.project_id,
        payload.target_type,
        payload.target_id,
        require_selectable=True,
    )

    follow_up.target_type = payload.target_type
    follow_up.target_id = payload.target_id
    follow_up.status = "linked"
    follow_up.linked_by = user_id
    follow_up.linked_at = utc_now()
    follow_up.updated_at = utc_now()
    db.commit()
    db.refresh(follow_up)
    return follow_up


def close_follow_up(
    db: Session,
    plan: PreconstructionComparisonPlan,
    review_set: PreconstructionReviewSet,
    follow_up: PreconstructionFindingFollowUp,
    user_id: int,
    payload,
    config: PreconstructionFollowUpConfig,
) -> PreconstructionFindingFollowUp:
    """Complete or cancel a follow-up. Terminal states are never reopened."""
    _require_writable(plan, review_set)
    if not follow_up_transition_allowed(follow_up.status, payload.status):
        raise _conflict(
            f"Cannot move a {follow_up.status} follow-up to {payload.status}"
        )
    note = sanitize_text(payload.closure_note)
    if note and len(note) > config.max_closure_note_characters:
        raise _unprocessable("Closure note exceeds the configured limit")
    if closure_note_required(payload.status) and not note:
        raise _unprocessable("A note is required when cancelling a follow-up")

    follow_up.status = payload.status
    follow_up.closure_note = note
    follow_up.closed_by = user_id
    follow_up.closed_at = utc_now()
    follow_up.updated_at = utc_now()
    db.commit()
    db.refresh(follow_up)
    return follow_up
