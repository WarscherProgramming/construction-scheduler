"""Response contracts for preconstruction execution metrics.

Read-only. Metric rows are written by the services that perform the work and
are never created, edited, or deleted through the API, so there is no mutation
model here. Payloads carry identifiers, counts, milliseconds, and units only:
never assertion text, evidence excerpts, reviewer notes, prompts, or provider
output.
"""

from datetime import datetime
from typing import Literal

from app.schemas.common import MutationModel


ExecutionKindValue = Literal[
    "preparation_run",
    "analysis_attempt",
    "scope_comparison",
    "evaluation_run",
]


class ExecutionMetricResponse(MutationModel):
    id: int
    execution_kind: str
    execution_kind_label: str
    execution_id: int
    metrics_version: str
    duration_ms: int
    phase_durations: dict
    query_count: int | None
    response_bytes: int | None
    input_units: int | None
    output_units: int | None
    estimated_cost_micros: int | None
    # Absent when no rate is configured, so a zero is never mistaken for a
    # measured cost of nothing.
    estimated_cost_display: str | None
    cost_rate_configured: bool
    manifest_reused: bool
    budget_stop_reason: str | None
    budget_stop_label: str | None
    recorded_at: datetime


class ExecutionMetricKindSummary(MutationModel):
    execution_kind: str
    execution_kind_label: str
    count: int
    total_duration_ms: int
    max_duration_ms: int
    average_duration_ms: int
    input_units: int | None
    output_units: int | None
    estimated_cost_micros: int | None


class ExecutionMetricSummaryResponse(MutationModel):
    total_executions: int
    total_duration_ms: int
    estimated_cost_micros: int | None
    estimated_cost_display: str | None
    cost_rate_configured: bool
    by_kind: list[ExecutionMetricKindSummary]


class ExecutionMetricListResponse(MutationModel):
    items: list[ExecutionMetricResponse]
    total: int
    limit: int
    offset: int
    summary: ExecutionMetricSummaryResponse
    metrics_enabled: bool
    metrics_version: str
