"""Request and response contracts for finding follow-up actions.

Every mutation model forbids unknown fields. Clients never supply project
identity, finding identity, lifecycle status, the pinned acceptance review,
draft template version, actor identity, or lifecycle timestamps; the server
computes all of them.

Nothing here creates an RFI, a Change Order, a Submittal, a relationship, or
any other authoritative record. A link references a record the human already
created through its own existing workflow.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import MutationModel, UpdateMutationModel


FollowUpActionValue = Literal[
    "rfi",
    "change_order",
    "submittal",
    "procurement_action",
    "subcontract_clarification",
    "internal_follow_up",
]
FollowUpStatusValue = Literal["planned", "linked", "completed", "cancelled"]
FollowUpTargetTypeValue = Literal["rfi", "change_order", "submittal"]
FollowUpClosureStatusValue = Literal["completed", "cancelled"]


class FollowUpCreate(MutationModel):
    action_type: FollowUpActionValue
    # Optional human overrides of the server-generated draft. Omitting them
    # keeps the deterministic draft exactly as generated.
    draft_title: str | None = Field(default=None, min_length=1, max_length=200)
    draft_body: str | None = Field(default=None, min_length=1, max_length=4000)


class FollowUpUpdate(UpdateMutationModel):
    draft_title: str | None = Field(default=None, min_length=1, max_length=200)
    draft_body: str | None = Field(default=None, min_length=1, max_length=4000)


class FollowUpLinkRequest(MutationModel):
    target_type: FollowUpTargetTypeValue
    target_id: int = Field(ge=1, le=2_147_483_647)


class FollowUpCloseRequest(MutationModel):
    status: FollowUpClosureStatusValue
    closure_note: str | None = Field(default=None, max_length=2000)


class FollowUpTargetResponse(MutationModel):
    type: str
    id: int
    identifier: str
    title: str
    status: str | None
    route: dict | None
    available: bool


class FollowUpResponse(MutationModel):
    id: int
    project_id: int
    review_set_id: int
    comparison_plan_id: int
    finding_id: int
    finding_review_id: int | None
    action_type: str
    action_label: str
    action_guidance: str
    status: str
    status_label: str
    target_type: str | None
    target_id: int | None
    target: FollowUpTargetResponse | None
    draft_title: str
    draft_body: str
    draft_template_version: str
    closure_note: str | None
    # Derived, never stored: true when the finding has since moved away from
    # accepted. The follow-up itself is never rewritten.
    finding_status: str
    finding_status_label: str
    finding_no_longer_accepted: bool
    can_edit_draft: bool
    can_link: bool
    can_close: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    linked_by: int | None
    linked_at: datetime | None
    closed_by: int | None
    closed_at: datetime | None


class FollowUpDraftResponse(MutationModel):
    action_type: str
    action_label: str
    action_guidance: str
    target_type: str | None
    draft_title: str
    draft_body: str
    draft_template_version: str


class FollowUpActionOption(MutationModel):
    value: str
    label: str
    description: str
    target_type: str | None
    guidance: str


class FollowUpDetailResponse(MutationModel):
    follow_up: FollowUpResponse


class FollowUpListResponse(MutationModel):
    items: list[FollowUpResponse]
    total: int
    limit: int
    offset: int
    actions: list[FollowUpActionOption]
    summary: dict


class FindingFollowUpListResponse(MutationModel):
    items: list[FollowUpResponse]
    total: int
    actions: list[FollowUpActionOption]
    available_actions: list[FollowUpActionOption]
    drafts: list[FollowUpDraftResponse]
    finding_status: str
    eligible: bool
