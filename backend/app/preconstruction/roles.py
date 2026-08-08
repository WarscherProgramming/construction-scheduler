from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRole:
    value: str
    label: str
    category: str


DOCUMENT_ROLES = (
    DocumentRole("drawing", "Drawing", "requirement"),
    DocumentRole("specification", "Specification", "requirement"),
    DocumentRole("addendum", "Addendum", "requirement"),
    DocumentRole("schedule", "Schedule", "requirement"),
    DocumentRole("equipment_schedule", "Equipment Schedule", "requirement"),
    DocumentRole("proposal", "Proposal", "coverage"),
    DocumentRole("subcontract", "Subcontract", "coverage"),
    DocumentRole("purchase_order", "Purchase Order", "coverage"),
    DocumentRole("procurement_package", "Procurement Package", "coverage"),
    DocumentRole("submittal", "Submittal", "coverage"),
    DocumentRole("rfi", "RFI", "context"),
    DocumentRole("change_order", "Change Order", "context"),
    DocumentRole("owner_directive", "Owner Directive", "context"),
    DocumentRole("other_reference", "Other Reference", "context"),
)
DOCUMENT_ROLE_BY_VALUE = {role.value: role for role in DOCUMENT_ROLES}

REVIEW_PURPOSES = {
    "bid_scope_review": "Bid Scope Review",
    "subcontract_scope_review": "Subcontract Scope Review",
    "procurement_review": "Procurement Review",
    "submittal_coverage_review": "Submittal Coverage Review",
    "revision_impact_review": "Revision Impact Review",
    "general_scope_review": "General Scope Review",
}

# Display labels for every analysis type the database permits. This map must
# stay total with respect to the ``preconstruction_analysis_runs`` type CHECK:
# ``run_response`` looks a run's type up here directly, so a stored value with
# no label would make the run listing and run detail routes fail for the whole
# review set. The two comparison types are labeled for that reason only —
# creating them over HTTP is still refused by the ``AnalysisType`` request
# literal, which deliberately does not list them.
ANALYSIS_TYPES = {
    "readiness_probe": "Readiness Probe",
    "provider_contract_validation": "Provider Contract Validation",
    "content_contract_validation": "Content Contract Validation",
    "scope_assertion_extraction": "Scope Assertion Extraction",
    "scope_comparison": "Scope Comparison",
    "scope_comparison_validation": "Scope Comparison Validation",
}

# Analysis types that require every active source to have a current prepared
# content snapshot pinned into the manifest.
CONTENT_DEPENDENT_ANALYSIS_TYPES = (
    "content_contract_validation",
    "scope_assertion_extraction",
)
