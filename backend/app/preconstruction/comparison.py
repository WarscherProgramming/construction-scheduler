"""Controlled vocabularies for cross-document scope comparison.

Pure constants and validation helpers: no ORM, no session, no configuration,
no I/O. Comparison types, finding types, severities, match classes, and review
reason codes are supplied by trusted code. A provider may select only from
these allowlists and can never introduce a comparison type, a finding type, a
severity, or a review decision of its own.

Findings are advisory. Nothing in this module expresses a legal conclusion:
there is deliberately no breach, liability, entitlement, or enforceability
vocabulary.
"""

from dataclasses import dataclass, field

from app.preconstruction.roles import DOCUMENT_ROLE_BY_VALUE


COMPARISON_SCHEMA_VERSION = "scope-comparison-1"
COMPARISON_MANIFEST_VERSION = "scope-comparison-manifest-1"
COMPARISON_TEMPLATE_VERSION = "scope-comparison-1"

# Analysis types added by M18.4. Deterministic comparison deliberately does not
# require a provider; provider validation is a separate, optional type.
DETERMINISTIC_COMPARISON_ANALYSIS_TYPE = "scope_comparison"
PROVIDER_COMPARISON_ANALYSIS_TYPE = "scope_comparison_validation"
COMPARISON_ANALYSIS_TYPES = (
    DETERMINISTIC_COMPARISON_ANALYSIS_TYPE,
    PROVIDER_COMPARISON_ANALYSIS_TYPE,
)

REQUIREMENT_ROLES = (
    "drawing",
    "specification",
    "addendum",
    "schedule",
    "equipment_schedule",
)
COVERAGE_ROLES = (
    "proposal",
    "subcontract",
    "purchase_order",
    "procurement_package",
    "submittal",
)


# --- finding types ----------------------------------------------------------

FINDING_TYPES = {
    "missing_coverage": "Missing coverage",
    "partial_coverage": "Partial coverage",
    "conflicting_scope": "Conflicting scope",
    "explicit_exclusion": "Explicit exclusion",
    "conditional_scope": "Conditional scope",
    "responsibility_conflict": "Responsibility conflict",
    "quantity_mismatch": "Quantity mismatch",
    "location_mismatch": "Location mismatch",
    "revision_added_scope": "Revision added scope",
    "revision_removed_scope": "Revision removed scope",
    "revision_changed_scope": "Revision changed scope",
    "duplicate_scope": "Duplicate scope",
    "unsupported_assertion": "Unsupported assertion",
    "informational_difference": "Informational difference",
}

FINDING_SEVERITIES = {
    "informational": "Informational",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "informational": 4,
}

# Deterministic default severity per finding type. A provider may propose a
# different severity only within DEFAULT-adjacent bounds (see
# ``normalize_provider_severity``); severity is always advisory and never
# accepts a finding on its own.
DEFAULT_SEVERITY_BY_FINDING_TYPE = {
    "missing_coverage": "high",
    "partial_coverage": "medium",
    "conflicting_scope": "high",
    "explicit_exclusion": "medium",
    "conditional_scope": "medium",
    "responsibility_conflict": "high",
    "quantity_mismatch": "medium",
    "location_mismatch": "medium",
    "revision_added_scope": "high",
    "revision_removed_scope": "high",
    "revision_changed_scope": "medium",
    "duplicate_scope": "low",
    "unsupported_assertion": "low",
    "informational_difference": "informational",
}


# --- match classification ---------------------------------------------------

MATCH_CLASSES = {
    "exact": "Exact",
    "strong": "Strong",
    "partial": "Partial",
    "weak": "Weak",
    "none": "No match",
}

MATCH_CLASS_ORDER = ("none", "weak", "partial", "strong", "exact")

# Documented, explainable component weights. There is no machine learning, no
# embedding, and no hidden weighting. The score is informational; the match
# class is authoritative and is always accompanied by explicit reason codes.
MATCH_WEIGHTS = {
    "concept_match": 40,
    "assertion_type_compatible": 10,
    "subject_exact": 20,
    "subject_overlap": 15,
    "requirement_overlap": 10,
    "specification_section_match": 10,
    "responsibility_match": 5,
    "discipline_match": 5,
    "trade_match": 5,
    "drawing_sheet_match": 5,
    "quantity_match": 5,
}
MATCH_SCORE_MAXIMUM = 100

# Thresholds are explicit. A candidate without a concept match can never rise
# above "weak", so lexical overlap alone never produces a strong match.
MATCH_CLASS_THRESHOLDS = (
    ("exact", 85),
    ("strong", 70),
    ("partial", 45),
    ("weak", 25),
)

MATCH_REASONS = {
    "concept_match": "Same taxonomy concept",
    "assertion_type_compatible": "Compatible assertion types",
    "subject_exact": "Identical normalized subject",
    "subject_overlap": "Overlapping subject wording",
    "requirement_overlap": "Overlapping requirement wording",
    "specification_section_match": "Same specification section",
    "drawing_sheet_match": "Same drawing sheet",
    "responsibility_match": "Same responsible party",
    "responsibility_mismatch": "Different responsible party",
    "discipline_match": "Same discipline",
    "trade_match": "Same trade",
    "quantity_match": "Same quantity and unit",
    "quantity_mismatch": "Different quantity",
    "unit_mismatch": "Different unit",
    "location_match": "Same location",
    "location_mismatch": "Different location",
    "inclusion_conflict": "One side includes and the other excludes",
    "conditional_inclusion": "Coverage is conditional",
    "revision_lineage": "Same drawing sheet across revisions",
}

# Material mismatches cap a candidate below "exact" no matter how well the
# lexical components score.
MATERIAL_MISMATCH_REASONS = (
    "responsibility_mismatch",
    "quantity_mismatch",
    "unit_mismatch",
    "location_mismatch",
    "inclusion_conflict",
)


# --- finding lifecycle ------------------------------------------------------

FINDING_STATUSES = {
    "proposed": "Proposed",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "needs_review": "Needs Review",
    "intentional_exclusion": "Intentional Exclusion",
    "superseded": "Superseded",
}

FINDING_ORIGINS = {
    "deterministic": "Deterministic",
    "provider_validated": "Provider validated",
    "manual": "Human authored",
}

FINDING_SET_STATUSES = {
    "completed": "Completed",
    "completed_with_warnings": "Completed with warnings",
    "failed_validation": "Failed validation",
}

FINDING_SIDES = {
    "requirement": "Requirement",
    "coverage": "Coverage",
    "context": "Context",
    "prior_revision": "Prior revision",
    "current_revision": "Current revision",
}

FINDING_LINK_ROLES = {
    "primary": "Primary",
    "supporting": "Supporting",
    "contradictory": "Contradictory",
    "near_match": "Near match",
}

FINDING_REVIEW_DECISIONS = {
    "accepted": "Accepted",
    "rejected": "Rejected",
    "needs_review": "Needs Review",
    "intentional_exclusion": "Intentional Exclusion",
}

FINDING_REVIEW_REASON_CODES = {
    "confirmed_gap": "Confirmed gap",
    "confirmed_conflict": "Confirmed conflict",
    "intentional_exclusion": "Intentional exclusion",
    "covered_elsewhere": "Covered elsewhere",
    "duplicate": "Duplicate",
    "incorrect_match": "Incorrect match",
    "insufficient_evidence": "Insufficient evidence",
    "wrong_comparison_type": "Wrong comparison type",
    "superseded_source": "Superseded source",
    "not_applicable": "Not applicable",
    "requires_trade_review": "Requires trade review",
    "requires_legal_review": "Requires legal review",
    "other": "Other",
}

DECISION_TO_FINDING_STATUS = {
    "accepted": "accepted",
    "rejected": "rejected",
    "needs_review": "needs_review",
    "intentional_exclusion": "intentional_exclusion",
}

# Settled decisions require a note to move away from.
SETTLED_FINDING_STATUSES = ("accepted", "rejected", "intentional_exclusion")
NOTE_REQUIRED_DECISIONS = ("rejected", "intentional_exclusion")

ALLOWED_FINDING_TRANSITIONS = {
    "proposed": ("accepted", "rejected", "needs_review", "intentional_exclusion"),
    "needs_review": ("accepted", "rejected", "intentional_exclusion"),
    "accepted": ("needs_review",),
    "rejected": ("needs_review",),
    "intentional_exclusion": ("needs_review",),
    "superseded": (),
}


# --- comparison types -------------------------------------------------------

@dataclass(frozen=True)
class ComparisonType:
    value: str
    label: str
    description: str
    left_roles: tuple[str, ...]
    right_roles: tuple[str, ...]
    allowed_finding_types: tuple[str, ...]
    provider_validation_eligible: bool = True
    revision_lineage: bool = False
    require_left: bool = True
    require_right: bool = True
    notes: str = ""


_COVERAGE_FINDING_TYPES = (
    "missing_coverage",
    "partial_coverage",
    "conflicting_scope",
    "explicit_exclusion",
    "conditional_scope",
    "responsibility_conflict",
    "quantity_mismatch",
    "location_mismatch",
    "duplicate_scope",
    "informational_difference",
)

_REVISION_FINDING_TYPES = (
    "revision_added_scope",
    "revision_removed_scope",
    "revision_changed_scope",
    "conflicting_scope",
    "quantity_mismatch",
    "location_mismatch",
    "informational_difference",
)


COMPARISON_TYPES = (
    ComparisonType(
        "requirement_vs_proposal",
        "Requirement vs Proposal",
        "Compare accepted requirement scope against a proposal's covered scope.",
        REQUIREMENT_ROLES,
        ("proposal",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "requirement_vs_subcontract",
        "Requirement vs Subcontract",
        "Compare accepted requirement scope against subcontracted scope.",
        REQUIREMENT_ROLES,
        ("subcontract",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "requirement_vs_purchase_order",
        "Requirement vs Purchase Order",
        "Compare accepted requirement scope against purchase-order coverage.",
        REQUIREMENT_ROLES,
        ("purchase_order",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "requirement_vs_procurement_package",
        "Requirement vs Procurement Package",
        "Compare accepted requirement scope against a procurement package.",
        REQUIREMENT_ROLES,
        ("procurement_package",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "requirement_vs_submittal",
        "Requirement vs Submittal",
        "Compare accepted requirement scope against submitted coverage.",
        REQUIREMENT_ROLES,
        ("submittal",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "specification_vs_drawing",
        "Specification vs Drawing",
        "Compare specification scope against drawing scope for consistency.",
        ("specification", "addendum"),
        ("drawing",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "drawing_vs_drawing_revision",
        "Drawing vs Drawing Revision",
        "Compare assertions across revisions of the same drawing sheet.",
        ("drawing",),
        ("drawing",),
        _REVISION_FINDING_TYPES,
        revision_lineage=True,
        notes=(
            "Structured assertion comparison across revision lineage. This is "
            "not a visual or image comparison of drawing content."
        ),
    ),
    ComparisonType(
        "proposal_vs_subcontract",
        "Proposal vs Subcontract",
        "Compare proposed scope against executed subcontract scope.",
        ("proposal",),
        ("subcontract",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "contract_vs_proposal",
        "Contract vs Proposal",
        "Compare subcontract scope against the proposal it was based on.",
        ("subcontract",),
        ("proposal",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "requirement_vs_change_order",
        "Requirement vs Change Order",
        "Compare accepted requirement scope against change-order scope.",
        REQUIREMENT_ROLES,
        ("change_order",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "equipment_schedule_vs_purchase_order",
        "Equipment Schedule vs Purchase Order",
        "Compare scheduled equipment against purchase-order coverage.",
        ("equipment_schedule",),
        ("purchase_order",),
        _COVERAGE_FINDING_TYPES,
    ),
    ComparisonType(
        "general_scope_coverage",
        "General Scope Coverage",
        "Compare all accepted requirement scope against all coverage scope.",
        REQUIREMENT_ROLES,
        COVERAGE_ROLES,
        _COVERAGE_FINDING_TYPES,
    ),
)

COMPARISON_TYPE_BY_VALUE = {item.value: item for item in COMPARISON_TYPES}
COMPARISON_TYPE_VALUES = tuple(item.value for item in COMPARISON_TYPES)


# ``requirement_vs_rfi`` is deliberately omitted. RFI is a context role, not a
# coverage role, so "requirement covered by RFI" is not a meaningful coverage
# relationship under the current role taxonomy.


# --- import-time validation -------------------------------------------------

if len(COMPARISON_TYPE_BY_VALUE) != len(COMPARISON_TYPES):
    raise RuntimeError("Duplicate comparison type value")
for _item in COMPARISON_TYPES:
    if not _item.left_roles or not _item.right_roles:
        raise RuntimeError(f"Comparison type {_item.value} needs both sides")
    for _role in (*_item.left_roles, *_item.right_roles):
        if _role not in DOCUMENT_ROLE_BY_VALUE:
            raise RuntimeError(f"Unknown document role {_role} in {_item.value}")
    for _finding_type in _item.allowed_finding_types:
        if _finding_type not in FINDING_TYPES:
            raise RuntimeError(f"Unknown finding type {_finding_type} in {_item.value}")
for _finding_type, _severity in DEFAULT_SEVERITY_BY_FINDING_TYPE.items():
    if _finding_type not in FINDING_TYPES:
        raise RuntimeError(f"Unknown finding type default {_finding_type}")
    if _severity not in FINDING_SEVERITIES:
        raise RuntimeError(f"Unknown default severity {_severity}")
if set(DEFAULT_SEVERITY_BY_FINDING_TYPE) != set(FINDING_TYPES):
    raise RuntimeError("Every finding type needs a documented default severity")
if set(MATCH_WEIGHTS) - set(MATCH_REASONS):
    raise RuntimeError("Every weighted component needs a documented reason code")
if sum(MATCH_WEIGHTS.values()) < MATCH_SCORE_MAXIMUM:
    raise RuntimeError("Match weights cannot reach the documented maximum")


# --- helpers ----------------------------------------------------------------

def resolve_comparison_type(value: str) -> ComparisonType | None:
    return COMPARISON_TYPE_BY_VALUE.get(value)


def comparison_type_payload(item: ComparisonType) -> dict:
    return {
        "value": item.value,
        "label": item.label,
        "description": item.description,
        "left_roles": list(item.left_roles),
        "right_roles": list(item.right_roles),
        "allowed_finding_types": list(item.allowed_finding_types),
        "provider_validation_eligible": item.provider_validation_eligible,
        "revision_lineage": item.revision_lineage,
        "notes": item.notes,
    }


def finding_type_allowed(comparison_type: str, finding_type: str) -> bool:
    item = COMPARISON_TYPE_BY_VALUE.get(comparison_type)
    return bool(item and finding_type in item.allowed_finding_types)


def default_severity(finding_type: str) -> str:
    return DEFAULT_SEVERITY_BY_FINDING_TYPE[finding_type]


def normalize_provider_severity(finding_type: str, proposed: str | None) -> str:
    """Clamp a provider-proposed severity to one step from the documented default.

    A provider may nudge severity but cannot escalate an informational
    difference into a critical issue, and cannot invent a severity value.
    """
    baseline = default_severity(finding_type)
    if proposed is None or proposed not in FINDING_SEVERITIES:
        return baseline
    order = list(SEVERITY_ORDER)
    baseline_index = order.index(baseline)
    proposed_index = order.index(proposed)
    if abs(proposed_index - baseline_index) <= 1:
        return proposed
    step = 1 if proposed_index > baseline_index else -1
    return order[baseline_index + step]


def classify_match(score: int, reasons: tuple[str, ...]) -> str:
    """Map an explainable score plus reason codes onto a named match class.

    Without a concept match the class is capped at ``weak``: lexical overlap
    alone never yields a strong or exact match. A material mismatch caps the
    class at ``strong``, so an exact match never hides a contradiction.
    """
    resolved = "none"
    for name, threshold in MATCH_CLASS_THRESHOLDS:
        if score >= threshold:
            resolved = name
            break
    if "concept_match" not in reasons:
        capped = MATCH_CLASS_ORDER.index("weak")
        if MATCH_CLASS_ORDER.index(resolved) > capped:
            resolved = "weak"
    if any(reason in MATERIAL_MISMATCH_REASONS for reason in reasons):
        capped = MATCH_CLASS_ORDER.index("strong")
        if MATCH_CLASS_ORDER.index(resolved) > capped:
            resolved = "strong"
    return resolved


def match_class_at_least(value: str, minimum: str) -> bool:
    return MATCH_CLASS_ORDER.index(value) >= MATCH_CLASS_ORDER.index(minimum)


def finding_transition_allowed(current_status: str, decision: str) -> bool:
    return decision in ALLOWED_FINDING_TRANSITIONS.get(current_status, ())


def finding_note_required(
    current_status: str, decision: str, reason_code: str | None
) -> bool:
    """Rejection, intentional exclusion, reversal, and "other" need a note."""
    return (
        decision in NOTE_REQUIRED_DECISIONS
        or current_status in SETTLED_FINDING_STATUSES
        or reason_code == "other"
    )
