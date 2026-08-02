from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.project_schedule_settings import (
    ProjectScheduleSettingsResponse,
)
from app.schemas.schedule_baseline import (
    CriticalChange,
    ScheduleBaselineComparisonUpdate,
    ScheduleBaselineCreate,
    ScheduleBaselineDetailResponse,
    ScheduleBaselineListResponse,
    ScheduleBaselineMutationResponse,
    ScheduleVarianceResponse,
)
from app.services.schedule_baseline import (
    archive_schedule_baseline,
    capture_schedule_baseline,
    get_schedule_baseline_detail,
    get_schedule_variance,
    list_schedule_baselines,
    select_comparison_baseline,
)


router = APIRouter()
BaselineListStatus = Literal["active", "archived", "all"]
VarianceStatus = Literal[
    "slipped",
    "improved",
    "unchanged",
    "added",
    "removed",
    "unscheduled",
    "incomparable",
]
VarianceSort = Literal[
    "wbs",
    "name",
    "baseline_start",
    "current_start",
    "baseline_finish",
    "current_finish",
    "start_variance",
    "finish_variance",
    "duration_variance",
    "status",
    "critical_change",
]


@router.post(
    "/projects/{project_id}/schedule-baselines",
    response_model=ScheduleBaselineMutationResponse,
    status_code=201,
)
def create_schedule_baseline(
    project_id: int,
    payload: ScheduleBaselineCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    baseline, comparison_baseline_id = capture_schedule_baseline(
        db,
        project_id=project_id,
        captured_by=current_user["id"],
        name=payload.name,
        description=payload.description,
    )
    return {
        "baseline": baseline,
        "comparison_baseline_id": comparison_baseline_id,
    }


@router.get(
    "/projects/{project_id}/schedule-baselines",
    response_model=ScheduleBaselineListResponse,
)
def get_schedule_baselines(
    project_id: int,
    response: Response,
    baseline_status: Annotated[
        BaselineListStatus,
        Query(alias="status"),
    ] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return list_schedule_baselines(
        db,
        project_id=project_id,
        status_filter=baseline_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/schedule-baselines/{baseline_id}",
    response_model=ScheduleBaselineDetailResponse,
)
def get_schedule_baseline(
    project_id: int,
    baseline_id: PositiveId,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return get_schedule_baseline_detail(
        db,
        project_id=project_id,
        baseline_id=baseline_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/schedule-baselines/{baseline_id}/archive",
    response_model=ScheduleBaselineMutationResponse,
)
def archive_project_schedule_baseline(
    project_id: int,
    baseline_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    baseline, comparison_baseline_id = archive_schedule_baseline(
        db,
        project_id=project_id,
        baseline_id=baseline_id,
    )
    return {
        "baseline": baseline,
        "comparison_baseline_id": comparison_baseline_id,
    }


@router.put(
    "/projects/{project_id}/schedule-baseline-comparison",
    response_model=ProjectScheduleSettingsResponse,
)
def update_schedule_baseline_comparison(
    project_id: int,
    payload: ScheduleBaselineComparisonUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return select_comparison_baseline(
        db,
        project_id=project_id,
        baseline_id=payload.baseline_id,
    )


@router.get(
    "/projects/{project_id}/schedule-variance",
    response_model=ScheduleVarianceResponse,
)
def get_project_schedule_variance(
    project_id: int,
    response: Response,
    baseline_id: Annotated[
        int | None,
        Query(ge=1, le=2_147_483_647),
    ] = None,
    include_summaries: bool = True,
    variance_status: Annotated[
        VarianceStatus | None,
        Query(alias="status"),
    ] = None,
    critical_change: CriticalChange | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort: VarianceSort = "wbs",
    order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    normalized_search = search.strip() if search else None
    return get_schedule_variance(
        db,
        project_id=project_id,
        baseline_id=baseline_id,
        include_summaries=include_summaries,
        status_filter=variance_status,
        critical_change_filter=critical_change,
        search=normalized_search or None,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
