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

ANALYSIS_TYPES = {
    "readiness_probe": "Readiness Probe",
    "provider_contract_validation": "Provider Contract Validation",
    "content_contract_validation": "Content Contract Validation",
}
