from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.look_ahead import (
    LookAheadItemUpdate,
    LookAheadPlanCreate,
    LookAheadPlanDetailResponse,
    LookAheadPlanListResponse,
    LookAheadPlanMutationResponse,
    LookAheadPlanUpdate,
)
from app.services.look_ahead import (
    archive_look_ahead_plan,
    create_look_ahead_plan,
    get_look_ahead_plan_detail,
    list_look_ahead_plans,
    update_look_ahead_item,
    update_look_ahead_plan,
)


router = APIRouter()
PlanListStatus = Literal["active", "archived", "all"]


@router.post(
    "/projects/{project_id}/look-ahead-plans",
    response_model=LookAheadPlanMutationResponse,
    status_code=201,
)
def create_project_look_ahead_plan(
    project_id: int,
    payload: LookAheadPlanCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    plan = create_look_ahead_plan(
        db,
        project_id=project_id,
        created_by=current_user["id"],
        **payload.model_dump(),
    )
    return {"plan": plan}


@router.get(
    "/projects/{project_id}/look-ahead-plans",
    response_model=LookAheadPlanListResponse,
)
def get_project_look_ahead_plans(
    project_id: int,
    response: Response,
    plan_status: Annotated[PlanListStatus, Query(alias="status")] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return list_look_ahead_plans(
        db,
        project_id=project_id,
        status_filter=plan_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/look-ahead-plans/{plan_id}",
    response_model=LookAheadPlanDetailResponse,
)
def get_project_look_ahead_plan(
    project_id: int,
    plan_id: PositiveId,
    response: Response,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return get_look_ahead_plan_detail(
        db,
        project_id=project_id,
        plan_id=plan_id,
    )


@router.put(
    "/projects/{project_id}/look-ahead-plans/{plan_id}",
    response_model=LookAheadPlanMutationResponse,
)
def update_project_look_ahead_plan(
    project_id: int,
    plan_id: PositiveId,
    payload: LookAheadPlanUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    plan = update_look_ahead_plan(
        db,
        project_id=project_id,
        plan_id=plan_id,
        values=payload.model_dump(exclude_unset=True),
    )
    return {"plan": plan}


@router.post(
    "/projects/{project_id}/look-ahead-plans/{plan_id}/archive",
    response_model=LookAheadPlanMutationResponse,
)
def archive_project_look_ahead_plan(
    project_id: int,
    plan_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    plan = archive_look_ahead_plan(
        db,
        project_id=project_id,
        plan_id=plan_id,
    )
    return {"plan": plan}


@router.put(
    "/projects/{project_id}/look-ahead-plans/{plan_id}/items/{task_id}",
    response_model=LookAheadPlanDetailResponse,
)
def update_project_look_ahead_item(
    project_id: int,
    plan_id: PositiveId,
    task_id: PositiveId,
    payload: LookAheadItemUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return update_look_ahead_item(
        db,
        project_id=project_id,
        plan_id=plan_id,
        task_id=task_id,
        updated_by=current_user["id"],
        values=payload.model_dump(exclude_unset=True),
    )
