from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import MutationModel, ORMModel, UpdateMutationModel
from app.schemas.task import ConstraintType, DateString, ProgressStatus


PlanStatus = Literal["active", "archived"]
ReadinessStatus = Literal[
    "unreviewed",
    "ready",
    "at_risk",
    "blocked",
    "committed",
    "complete",
]
ConstraintCategory = Literal[
    "predecessor_work",
    "design_information",
    "submittal",
    "material",
    "labor",
    "equipment",
    "access",
    "inspection",
    "permit",
    "owner_decision",
    "safety",
    "weather",
    "other",
]
LookAheadName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
OptionalDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2_000),
]
OptionalOwner = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=255),
]
OptionalOverride = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=1_000),
]
PositiveId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class LookAheadPlanCreate(MutationModel):
    name: LookAheadName
    description: OptionalDescription | None = None
    anchor_date: DateString | None = None
    window_days: int = Field(default=21, ge=7, le=42)


class LookAheadPlanUpdate(UpdateMutationModel):
    name: LookAheadName | None = None
    description: OptionalDescription | None = None
    anchor_date: DateString | None = None
    window_days: int | None = Field(default=None, ge=7, le=42)

    @field_validator("name", "anchor_date", "window_days")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class LookAheadItemUpdate(UpdateMutationModel):
    readiness_status: ReadinessStatus | None = None
    blocking_reason: OptionalDescription | None = None
    constraint_category: ConstraintCategory | None = None
    constraint_owner: OptionalOwner | None = None
    target_resolution_date: DateString | None = None
    commitment_note: OptionalDescription | None = None
    responsible_company_id: PositiveId | None = None
    manually_included: bool | None = None
    manually_excluded: bool | None = None
    override_reason: OptionalOverride | None = None

    @field_validator("readiness_status", "manually_included", "manually_excluded")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_manual_flags(self):
        if self.manually_included and self.manually_excluded:
            raise ValueError("A task cannot be manually included and excluded")
        return self


class LookAheadPlanResponse(ORMModel):
    id: int
    project_id: int
    name: str
    description: str | None
    anchor_date: str
    window_days: int
    status: PlanStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class LookAheadPlanListResponse(BaseModel):
    plans: list[LookAheadPlanResponse]
    total: int
    limit: int
    offset: int


class LookAheadCompanyResponse(BaseModel):
    id: int
    name: str
    trade: str | None


class LookAheadItemResponse(BaseModel):
    task_id: int
    task_available: bool
    name: str | None
    wbs: str | None
    order_index: int | None
    start_date: str | None
    end_date: str | None
    progress_status: ProgressStatus | None
    percent_complete: int | None
    is_milestone: bool
    is_critical: bool
    out_of_sequence: bool
    out_of_sequence_reason: str | None
    constraint_type: ConstraintType | None
    constraint_date: str | None
    predecessor_count: int
    readiness_status: ReadinessStatus
    blocking_reason: str | None
    constraint_category: ConstraintCategory | None
    constraint_owner: str | None
    target_resolution_date: str | None
    commitment_note: str | None
    responsible_company: LookAheadCompanyResponse | None
    manually_included: bool
    manually_excluded: bool
    override_reason: str | None
    updated_by: int | None
    updated_at: datetime | None
    section: Literal["carryover", "week", "manual", "excluded"]
    week_index: int | None
    overdue: bool
    starts_this_week: bool
    continues_from_prior_week: bool
    spans_multiple_weeks: bool
    blocked: bool
    constraint_due: bool
    commitment_missing: bool
    unscheduled: bool


class LookAheadWeekResponse(BaseModel):
    week_index: int
    start_date: str
    end_date: str
    items: list[LookAheadItemResponse]


class LookAheadSummaryResponse(BaseModel):
    total_items: int
    week_counts: list[int]
    carryover_count: int
    manual_count: int
    ready_count: int
    at_risk_count: int
    blocked_count: int
    committed_count: int
    overdue_count: int
    critical_count: int
    out_of_sequence_count: int
    milestones_count: int
    constraints_due_count: int
    unassigned_company_count: int
    unscheduled_count: int


class LookAheadPlanDetailResponse(BaseModel):
    plan: LookAheadPlanResponse
    current_data_date: str
    window_end_date: str
    summary: LookAheadSummaryResponse
    carryover_items: list[LookAheadItemResponse]
    weeks: list[LookAheadWeekResponse]
    manual_items: list[LookAheadItemResponse]
    excluded_items: list[LookAheadItemResponse]


class LookAheadPlanMutationResponse(BaseModel):
    plan: LookAheadPlanResponse
