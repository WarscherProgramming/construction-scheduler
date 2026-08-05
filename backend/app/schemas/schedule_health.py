from datetime import datetime
from typing import Literal

from pydantic import BaseModel


HealthCategory = Literal["stable", "attention", "critical"]
HealthSeverity = Literal["attention", "critical"]


class ScheduleHealthReason(BaseModel):
    code: str
    label: str
    severity: HealthSeverity
    value: int


class ScheduleHealthThresholds(BaseModel):
    critical_finish_variance_workdays: int
    reason_limit: int
    attention_item_limit: int


class ScheduleHealthBaseline(BaseModel):
    id: int
    name: str
    captured_at: datetime
    project_finish: str | None


class ScheduleHealthMetrics(BaseModel):
    project_finish_variance_workdays: int | None
    slipped_tasks: int
    newly_critical_tasks: int
    negative_float_tasks: int
    out_of_sequence_tasks: int
    overdue_incomplete_tasks: int
    constraint_violations: int
    mandatory_constraint_violations: int
    blocked_look_ahead_items: int
    blocked_critical_look_ahead_items: int
    overdue_look_ahead_blockers: int
    committed_look_ahead_items: int
    resource_overallocated_days: int
    labor_overallocated_days: int
    equipment_overallocated_days: int
    unavailable_resource_conflicts: int
    unassigned_executable_tasks: int
    milestone_variance_count: int
    milestones_due_next_21_days: int


class ExecutiveScheduleSummary(BaseModel):
    schedule_start_date: str
    data_date: str
    baseline_name: str | None
    baseline_captured_at: datetime | None
    baseline_project_finish: str | None
    current_forecast_finish: str | None
    project_finish_variance_workdays: int | None
    total_leaf_tasks: int
    not_started_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    slipped_tasks: int
    newly_critical_tasks: int
    negative_float_tasks: int
    out_of_sequence_tasks: int
    milestones_due_next_21_days: int
    blocked_look_ahead_items: int
    committed_look_ahead_items: int
    labor_overallocated_days: int
    equipment_overallocated_days: int
    unassigned_executable_tasks: int


class ScheduleAttentionItem(BaseModel):
    severity: HealthSeverity
    source: Literal["task", "look_ahead", "resource"]
    code: str
    task_id: int | None
    title: str
    wbs: str | None
    due_date: str | None
    reason: str
    target_page: Literal["schedule"] = "schedule"


class ScheduleHealthResponse(BaseModel):
    category: HealthCategory
    summary: str
    reasons: list[ScheduleHealthReason]
    metrics: ScheduleHealthMetrics
    thresholds: ScheduleHealthThresholds
    baseline: ScheduleHealthBaseline | None
    data_date: str
    schedule_start_date: str
    executive_summary: ExecutiveScheduleSummary
    top_attention_items: list[ScheduleAttentionItem]

