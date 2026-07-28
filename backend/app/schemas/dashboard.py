from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel


class DashboardProjectSummary(BaseModel):
    id: int
    name: str


class DashboardScheduleSummary(BaseModel):
    task_count: int
    planned_start: date | None
    planned_finish: date | None
    past_planned_finish_count: int
    upcoming_start_count: int


class DashboardRFISummary(BaseModel):
    total: int
    open: int
    overdue: int
    due_soon: int


class DashboardSubmittalSummary(BaseModel):
    total: int
    pending: int
    overdue: int
    due_soon: int


class DashboardPunchItemSummary(BaseModel):
    total: int
    open: int
    overdue: int
    completed_last_7_days: int


class DashboardChangeOrderSummary(BaseModel):
    total: int
    active: int
    approved: int
    rejected: int
    unknown_status: int
    active_value: str
    approved_value: str


class DashboardDailyLogSummary(BaseModel):
    total: int
    latest_log_date: date | None
    today_count: int
    today_manpower: int
    last_7_days_count: int


class DashboardRecentDocument(BaseModel):
    id: int
    parent_type: str
    parent_id: int
    filename: str
    file_size: int
    created_at: AwareDatetime


class DashboardDocumentSummary(BaseModel):
    total: int
    uploaded_last_7_days: int
    recent: list[DashboardRecentDocument]


class DashboardAttentionItem(BaseModel):
    resource_type: Literal["task", "rfi", "submittal", "punch_item"]
    record_id: int
    identifier: str
    title: str
    due_date: date
    reason: Literal["Overdue", "Past planned finish"]
    severity: Literal["overdue", "informational"]
    target_page: Literal["schedule", "rfis", "submittals", "punch-items"]


class DashboardUpcomingTask(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date | None
    duration: int | None


class DashboardRecentUpdate(BaseModel):
    resource_type: Literal[
        "rfi",
        "submittal",
        "punch_item",
        "change_order",
        "attachment",
    ]
    record_id: int
    identifier: str
    description: str
    updated_at: AwareDatetime
    target_page: str


class DashboardResponse(BaseModel):
    as_of: date
    generated_at: AwareDatetime
    project: DashboardProjectSummary
    schedule: DashboardScheduleSummary
    rfis: DashboardRFISummary
    submittals: DashboardSubmittalSummary
    punch_items: DashboardPunchItemSummary
    change_orders: DashboardChangeOrderSummary
    daily_logs: DashboardDailyLogSummary
    documents: DashboardDocumentSummary
    attention_items: list[DashboardAttentionItem]
    upcoming_tasks: list[DashboardUpcomingTask]
    recent_updates: list[DashboardRecentUpdate]
