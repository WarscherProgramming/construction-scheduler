"""Controlled vocabulary for human-initiated follow-up actions on findings.

Pure constants, draft templates, and validation helpers: no ORM, no session,
no configuration, no I/O.

A follow-up records that a person decided to act on an accepted M18.4 finding
and, once they have acted, which existing project record answers it. It is an
*intent plus a link*. It is not a task system, not an approval chain, not a
second review system, and it never creates, approves, or mutates an RFI, a
Change Order, a Submittal, a relationship, or any other authoritative record.

The generated draft is a starting point for a human to edit inside the existing
workflow dialog. Nothing here expresses a legal conclusion: there is
deliberately no breach, liability, entitlement, claim, or damages vocabulary.
"""

from dataclasses import dataclass

# ``relationship_rules`` is itself a pure constants module with no ORM, session,
# or I/O. Importing it keeps ENTITY_TYPES the single source of truth for what a
# follow-up may point at, rather than copying the list and letting the two
# drift apart.
from app.services.relationship_rules import ENTITY_TYPES


FOLLOW_UP_SCHEMA_VERSION = "scope-follow-up-1"
FOLLOW_UP_TEMPLATE_VERSION = "scope-follow-up-draft-1"

# A follow-up may only be raised from a finding a human has explicitly
# accepted. ``intentional_exclusion`` is deliberately excluded: that status is
# the recorded decision *not* to act, so raising work from it would contradict
# a human judgement.
FOLLOW_UP_ELIGIBLE_FINDING_STATUSES = ("accepted",)


# --- action types -----------------------------------------------------------

@dataclass(frozen=True)
class FollowUpAction:
    value: str
    label: str
    description: str
    # The relationship entity type this action can be linked to once the human
    # has created the record. ``None`` means the action is tracked but has no
    # authoritative record to point at in this milestone.
    target_type: str | None
    guidance: str


FOLLOW_UP_ACTIONS = (
    FollowUpAction(
        "rfi",
        "Request for Information",
        "Ask the design team to clarify the scope this finding raises.",
        "rfi",
        "Create the RFI in the project RFI workflow, then link it here.",
    ),
    FollowUpAction(
        "change_order",
        "Change Order",
        "Track a commercial change arising from this finding.",
        "change_order",
        "Create the Change Order in the project workflow, then link it here.",
    ),
    FollowUpAction(
        "submittal",
        "Submittal",
        "Track a submittal that would resolve this coverage question.",
        "submittal",
        "Create the Submittal in the project workflow, then link it here.",
    ),
    FollowUpAction(
        "procurement_action",
        "Procurement Action",
        "Record procurement work to be carried out outside FieldFlow.",
        None,
        "Record the outcome in the closure note when the work is done.",
    ),
    FollowUpAction(
        "subcontract_clarification",
        "Subcontract Clarification",
        "Record a scope clarification to raise with the subcontractor.",
        None,
        "Record the outcome in the closure note when the work is done.",
    ),
    FollowUpAction(
        "internal_follow_up",
        "Internal Follow-Up",
        "Record internal coordination work with no external record.",
        None,
        "Record the outcome in the closure note when the work is done.",
    ),
)

FOLLOW_UP_ACTION_BY_VALUE = {item.value: item for item in FOLLOW_UP_ACTIONS}
FOLLOW_UP_ACTION_VALUES = tuple(item.value for item in FOLLOW_UP_ACTIONS)
FOLLOW_UP_TARGET_TYPES = tuple(
    sorted({item.target_type for item in FOLLOW_UP_ACTIONS if item.target_type})
)


# --- lifecycle --------------------------------------------------------------

FOLLOW_UP_STATUSES = {
    "planned": "Planned",
    "linked": "Linked",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

# A follow-up carries a lifecycle, not a judgement. The finding's own
# append-only review history remains the sole authority on whether the finding
# is valid, so there is no second decision vocabulary here.
ALLOWED_FOLLOW_UP_TRANSITIONS = {
    "planned": ("linked", "completed", "cancelled"),
    "linked": ("completed", "cancelled"),
    "completed": (),
    "cancelled": (),
}

CLOSED_FOLLOW_UP_STATUSES = ("completed", "cancelled")
ACTIVE_FOLLOW_UP_STATUSES = ("planned", "linked")

# Cancelling discards planned work, so it always needs a stated reason.
CLOSURE_NOTE_REQUIRED_STATUSES = ("cancelled",)


# --- draft assembly ---------------------------------------------------------

ADVISORY_NOTICE = (
    "Raised from a FieldFlow preconstruction scope review finding. "
    "The finding is advisory and has been accepted for follow-up by a "
    "reviewer. Please confirm the wording below before sending."
)

# Deliberately neutral phrasing. These templates describe what was observed and
# ask a question; they never assert an obligation, a fault, or a cost position.
DRAFT_OPENINGS = {
    "rfi": "Please clarify the following scope question identified during review.",
    "change_order": "The following scope difference was identified during review.",
    "submittal": "The following scope item may need a submittal to confirm coverage.",
    "procurement_action": "The following scope item may need procurement follow-up.",
    "subcontract_clarification": (
        "The following scope item may need clarification with the subcontractor."
    ),
    "internal_follow_up": "The following scope item needs internal follow-up.",
}

DRAFT_CLOSINGS = {
    "rfi": "Please confirm the intended scope and responsibility.",
    "change_order": "Please confirm whether this difference changes the scope of work.",
    "submittal": "Please confirm whether a submittal is required for this item.",
    "procurement_action": "Please confirm the procurement path for this item.",
    "subcontract_clarification": "Please confirm the intended subcontract scope.",
    "internal_follow_up": "Please confirm the intended resolution.",
}

MAX_DRAFT_SUBJECTS = 6
MAX_DRAFT_CITATIONS = 6

# Language that must never appear in a generated draft or in any controlled
# label. A follow-up draft heads toward a contractual document, so the
# vocabulary stays descriptive.
FORBIDDEN_DRAFT_TERMS = (
    "breach",
    "liability",
    "liable",
    "entitlement",
    "entitled",
    "damages",
    "negligence",
    "default",
    "termination",
    "warranty claim",
)


@dataclass(frozen=True)
class DraftContext:
    """Everything the draft templates are allowed to see.

    Every field is derived server-side from stored finding data. No client
    text and no provider response reaches this structure unmodified: summaries
    arrive already sanitized and length-bounded by the service layer.
    """

    action_type: str
    finding_type_label: str
    severity_label: str
    comparison_type_label: str
    finding_title: str
    finding_summary: str | None
    requirement_subjects: tuple[str, ...]
    coverage_subjects: tuple[str, ...]
    evidence_citations: tuple[str, ...]


def _bullet_block(heading: str, values: tuple[str, ...], limit: int) -> list[str]:
    if not values:
        return []
    lines = [heading]
    lines.extend(f"- {value}" for value in values[:limit])
    if len(values) > limit:
        lines.append(f"- ... and {len(values) - limit} more")
    return lines


def build_draft_title(context: DraftContext) -> str:
    """Deterministic subject line. Same context in, same title out."""
    return f"{context.finding_type_label}: {context.finding_title}"


def build_draft_body(context: DraftContext) -> str:
    """Deterministic plain-text body. No Markdown, no HTML, no links."""
    lines = [
        DRAFT_OPENINGS[context.action_type],
        "",
        f"Finding: {context.finding_title}",
        f"Type: {context.finding_type_label}",
        f"Severity: {context.severity_label}",
        f"Comparison: {context.comparison_type_label}",
    ]
    if context.finding_summary:
        lines.extend(["", f"Summary: {context.finding_summary}"])
    requirement = _bullet_block(
        "Requirement scope reviewed:",
        context.requirement_subjects,
        MAX_DRAFT_SUBJECTS,
    )
    if requirement:
        lines.append("")
        lines.extend(requirement)
    coverage = _bullet_block(
        "Coverage scope reviewed:",
        context.coverage_subjects,
        MAX_DRAFT_SUBJECTS,
    )
    if coverage:
        lines.append("")
        lines.extend(coverage)
    citations = _bullet_block(
        "Source references:",
        context.evidence_citations,
        MAX_DRAFT_CITATIONS,
    )
    if citations:
        lines.append("")
        lines.extend(citations)
    lines.extend(["", DRAFT_CLOSINGS[context.action_type], "", ADVISORY_NOTICE])
    return "\n".join(lines)


def resolve_action(value: str) -> FollowUpAction | None:
    return FOLLOW_UP_ACTION_BY_VALUE.get(value)


def action_payload(item: FollowUpAction) -> dict:
    return {
        "value": item.value,
        "label": item.label,
        "description": item.description,
        "target_type": item.target_type,
        "guidance": item.guidance,
    }


def follow_up_transition_allowed(current_status: str, next_status: str) -> bool:
    return next_status in ALLOWED_FOLLOW_UP_TRANSITIONS.get(current_status, ())


def closure_note_required(next_status: str) -> bool:
    return next_status in CLOSURE_NOTE_REQUIRED_STATUSES


def target_required(action_type: str) -> bool:
    """Only actions with a resolvable authoritative record can be linked."""
    action = FOLLOW_UP_ACTION_BY_VALUE.get(action_type)
    return bool(action and action.target_type)


# --- import-time validation -------------------------------------------------

if len(FOLLOW_UP_ACTION_BY_VALUE) != len(FOLLOW_UP_ACTIONS):
    raise RuntimeError("Duplicate follow-up action value")
for _action in FOLLOW_UP_ACTIONS:
    if _action.target_type is not None and _action.target_type not in ENTITY_TYPES:
        raise RuntimeError(
            f"Unknown relationship entity type {_action.target_type} "
            f"in follow-up action {_action.value}"
        )
    if _action.value not in DRAFT_OPENINGS or _action.value not in DRAFT_CLOSINGS:
        raise RuntimeError(f"Follow-up action {_action.value} needs draft templates")
if set(DRAFT_OPENINGS) != set(FOLLOW_UP_ACTION_VALUES):
    raise RuntimeError("Draft openings must cover exactly the known actions")
if set(DRAFT_CLOSINGS) != set(FOLLOW_UP_ACTION_VALUES):
    raise RuntimeError("Draft closings must cover exactly the known actions")
if set(ALLOWED_FOLLOW_UP_TRANSITIONS) != set(FOLLOW_UP_STATUSES):
    raise RuntimeError("Every follow-up status needs a documented transition set")
for _status, _targets in ALLOWED_FOLLOW_UP_TRANSITIONS.items():
    for _target in _targets:
        if _target not in FOLLOW_UP_STATUSES:
            raise RuntimeError(f"Unknown follow-up transition target {_target}")

_VOCABULARY = " ".join(
    (
        *FOLLOW_UP_ACTION_VALUES,
        *(item.label for item in FOLLOW_UP_ACTIONS),
        *(item.description for item in FOLLOW_UP_ACTIONS),
        *(item.guidance for item in FOLLOW_UP_ACTIONS),
        *FOLLOW_UP_STATUSES.values(),
        *DRAFT_OPENINGS.values(),
        *DRAFT_CLOSINGS.values(),
        ADVISORY_NOTICE,
    )
).lower()
for _term in FORBIDDEN_DRAFT_TERMS:
    if _term in _VOCABULARY:
        raise RuntimeError(
            f"Follow-up vocabulary must not express a legal conclusion: {_term}"
        )
