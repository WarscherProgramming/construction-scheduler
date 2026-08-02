from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import MutationModel, ORMModel


BaselineStatus = Literal["active", "archived"]
ComparisonStatus = Literal[
    "slipped",
    "improved",
    "unchanged",
    "added",
    "removed",
    "unscheduled",
    "incomparable",
]
CriticalChange = Literal[
    "newly_critical",
    "no_longer_critical",
    "remained_critical",
    "remained_noncritical",
]
BaselineName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
BaselineDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2_000),
]
PositiveBaselineId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class ScheduleBaselineCreate(MutationModel):
    name: BaselineName
    description: BaselineDescription | None = None


class ScheduleBaselineResponse(ORMModel):
    id: int
    project_id: int
    name: str
    description: str | None
    captured_at: datetime
    captured_by: int
    schedule_start_date: str
    task_count: int
    status: BaselineStatus
    archived_at: datetime | None
    created_at: datetime


class ScheduleBaselineListResponse(BaseModel):
    baselines: list[ScheduleBaselineResponse]
    comparison_baseline_id: int | None
    total: int
    limit: int
    offset: int


class ScheduleBaselineTaskResponse(ORMModel):
    id: int
    baseline_id: int
    project_id: int
    task_id: int
    name: str
    order_index: int | None
    parent_task_id: int | None
    predecessor_task_id: int | None
    dependency_type: Literal["FS", "SS"]
    lag_days: int
    duration: int
    manual_start_date: str | None
    start_date: str | None
    end_date: str | None
    is_summary: bool
    was_critical: bool
    total_float: int | None
    wbs_path: str
    created_at: datetime


class ScheduleBaselineDetailResponse(BaseModel):
    baseline: ScheduleBaselineResponse
    tasks: list[ScheduleBaselineTaskResponse]
    total: int
    limit: int
    offset: int


class ScheduleBaselineMutationResponse(BaseModel):
    baseline: ScheduleBaselineResponse
    comparison_baseline_id: int | None


class ScheduleBaselineComparisonUpdate(MutationModel):
    baseline_id: PositiveBaselineId | None


class ScheduleVarianceTaskResponse(BaseModel):
    task_id: int
    baseline_task_id: int | None
    name: str
    wbs: str
    baseline_wbs: str | None
    current_wbs: str | None
    is_summary: bool
    current_start_date: str | None
    current_end_date: str | None
    baseline_start_date: str | None
    baseline_end_date: str | None
    start_variance_workdays: int | None
    finish_variance_workdays: int | None
    current_duration: int | None
    baseline_duration: int | None
    duration_variance_days: int | None
    current_total_float: int | None
    baseline_total_float: int | None
    float_variance_workdays: int | None
    current_critical: bool | None
    baseline_critical: bool | None
    critical_change: CriticalChange | None
    comparison_status: ComparisonStatus
    hierarchy_changed: bool
    dependency_changed: bool
    duration_changed: bool
    manual_start_changed: bool
    order_changed: bool


class ScheduleVarianceSummaryResponse(BaseModel):
    baseline_id: int
    baseline_name: str
    captured_at: datetime
    baseline_schedule_start_date: str
    current_schedule_start_date: str
    baseline_task_count: int
    current_task_count: int
    baseline_leaf_task_count: int
    current_leaf_task_count: int
    slipped_count: int
    improved_count: int
    unchanged_count: int
    added_count: int
    removed_count: int
    unscheduled_count: int
    incomparable_count: int
    baseline_project_finish: str | None
    current_project_finish: str | None
    project_finish_variance_workdays: int | None
    baseline_critical_count: int
    current_critical_count: int
    newly_critical_count: int
    no_longer_critical_count: int


class ScheduleVarianceResponse(BaseModel):
    baseline: ScheduleBaselineResponse | None
    summary: ScheduleVarianceSummaryResponse | None
    tasks: list[ScheduleVarianceTaskResponse]
    total: int
    limit: int
    offset: int
