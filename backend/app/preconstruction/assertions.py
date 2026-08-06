"""Controlled vocabularies for scope assertions and human review.

Pure constants. Providers may select only from these allowlists; review
decisions and reason codes are supplied by humans through the owned API.
"""


ASSERTION_SCHEMA_VERSION = "scope-assertion-1"

ASSERTION_TYPES = {
    "requirement": "Requirement",
    "physical_item": "Physical Item",
    "system": "System",
    "activity": "Activity",
    "responsibility": "Responsibility",
    "deliverable": "Deliverable",
    "testing_requirement": "Testing Requirement",
    "coordination_requirement": "Coordination Requirement",
    "procurement_requirement": "Procurement Requirement",
    "allowance": "Allowance",
    "alternate": "Alternate",
    "exclusion": "Exclusion",
    "informational": "Informational",
}

INCLUSION_STATES = {
    "included": "Included",
    "excluded": "Excluded",
    "conditional": "Conditional",
    "not_applicable": "Not Applicable",
    "unspecified": "Unspecified",
}

ASSERTION_STATUSES = {
    "proposed": "Proposed",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "needs_review": "Needs Review",
    "superseded": "Superseded",
}

ASSERTION_ORIGINS = {
    "provider": "Extracted",
    "manual": "Human authored",
}

ASSERTION_SET_STATUSES = {
    "completed": "Completed",
    "completed_with_warnings": "Completed with warnings",
    "failed_validation": "Failed validation",
}

EVIDENCE_ROLES = {
    "primary": "Primary",
    "supporting": "Supporting",
    "contextual": "Contextual",
    "contradictory": "Contradictory",
}

REVIEW_DECISIONS = {
    "accepted": "Accepted",
    "rejected": "Rejected",
    "needs_review": "Needs Review",
}

REVIEW_REASON_CODES = {
    "unsupported_by_evidence": "Unsupported by evidence",
    "incorrect_concept": "Incorrect concept",
    "incorrect_scope_interpretation": "Incorrect scope interpretation",
    "duplicate": "Duplicate",
    "irrelevant": "Irrelevant",
    "intentional_exclusion": "Intentional exclusion",
    "insufficient_detail": "Insufficient detail",
    "wrong_responsibility": "Wrong responsibility",
    "wrong_quantity": "Wrong quantity",
    "wrong_location": "Wrong location",
    "source_superseded": "Source superseded",
    "other": "Other",
}

# A human decision maps onto exactly one assertion lifecycle status. There is
# no confidence threshold and no provider-driven transition.
DECISION_TO_STATUS = {
    "accepted": "accepted",
    "rejected": "rejected",
    "needs_review": "needs_review",
}

# Reviewing away from a settled decision, rejecting, or selecting "other"
# requires an explicit note so the history stays auditable.
REVERSIBLE_FROM_STATUSES = ("accepted", "rejected")
NOTE_REQUIRED_DECISIONS = ("rejected",)

# Allowed human transitions. Provider extraction always produces "proposed".
ALLOWED_REVIEW_TRANSITIONS = {
    "proposed": ("accepted", "rejected", "needs_review"),
    "needs_review": ("accepted", "rejected"),
    "accepted": ("needs_review",),
    "rejected": ("needs_review",),
    "superseded": (),
}

PROVIDER_ASSERTION_LIMITS = {
    "subject": 300,
    "requirement_text": 2000,
    "responsibility_party": 200,
    "discipline": 120,
    "trade": 120,
    "specification_section": 60,
    "drawing_sheet": 100,
    "location_text": 300,
    "confidence_basis": 300,
    "provider_assertion_key": 100,
    "quantity_unit": 40,
}

REVIEWER_NOTE_LIMIT = 2000
EVIDENCE_EXCERPT_LIMIT = 600


def assertion_type_label(value: str) -> str:
    return ASSERTION_TYPES[value]


def inclusion_state_label(value: str) -> str:
    return INCLUSION_STATES[value]


def assertion_status_label(value: str) -> str:
    return ASSERTION_STATUSES[value]


def review_reason_label(value: str | None) -> str | None:
    return REVIEW_REASON_CODES[value] if value else None


def transition_allowed(current_status: str, decision: str) -> bool:
    return decision in ALLOWED_REVIEW_TRANSITIONS.get(current_status, ())


def note_required(current_status: str, decision: str, reason_code: str | None) -> bool:
    """A note is mandatory for rejection, reversal, or an "other" reason."""
    return (
        decision in NOTE_REQUIRED_DECISIONS
        or current_status in REVERSIBLE_FROM_STATUSES
        or reason_code == "other"
    )
