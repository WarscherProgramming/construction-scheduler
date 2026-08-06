from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    CollectionPage,
    PositiveId,
    get_collection_page,
    get_db,
    get_owned_project,
    get_preconstruction_config,
    get_preconstruction_preparation_config,
)
from app.core.config import PreconstructionAIConfig, PreconstructionPreparationConfig
from app.core.security import get_current_user
from app.models.project import Project
from app.preconstruction.factory import build_preconstruction_provider
from app.preconstruction.provider import PreconstructionAIProvider
from app.preconstruction.roles import DOCUMENT_ROLES
from app.schemas.common import MessageResponse
from app.schemas.preconstruction import (
    AnalysisRunCreate,
    AnalysisRunListResponse,
    AnalysisRunResponse,
    ContentInspectionResponse,
    PreparationRequest,
    PreparationRunResponse,
    ReadinessResponse,
    ReviewSetCreate,
    ReviewSetListResponse,
    ReviewSetResponse,
    ReviewSetUpdate,
    ReviewSourceCreate,
    ReviewSourceListResponse,
    ReviewSourceResponse,
    ReviewSourceUpdate,
    SourceCandidateListResponse,
)
from app.services.preconstruction import (
    add_review_source,
    archive_review_set,
    cancel_analysis_run,
    create_analysis_run,
    create_review_set,
    get_analysis_run,
    get_review_set,
    get_review_source,
    list_analysis_runs,
    list_review_sets,
    list_review_sources,
    list_source_candidates,
    remove_review_source,
    retry_analysis_run,
    review_readiness,
    review_set_response,
    run_response,
    source_response,
    update_review_set,
    update_review_source,
)
from app.services.preconstruction_content import (
    cancel_preparation_run,
    get_preparation_run,
    get_preparation_source,
    inspect_source_content,
    preparation_run_response,
    request_source_preparation,
    retry_preparation_run,
    source_preparation_states,
)


router = APIRouter(prefix="/projects/{project_id}/preconstruction")


def get_preconstruction_provider(
    config: PreconstructionAIConfig = Depends(get_preconstruction_config),
) -> PreconstructionAIProvider:
    return build_preconstruction_provider(config)


@router.post("/review-sets", response_model=ReviewSetResponse, status_code=201)
def create_review_set_route(
    project_id: int,
    payload: ReviewSetCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return review_set_response(
        create_review_set(db, project_id, current_user["id"], payload)
    )


@router.get("/review-sets", response_model=ReviewSetListResponse)
def list_review_sets_route(
    project_id: int,
    state: Literal["active", "archived", "all"] = "active",
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    page: CollectionPage = Depends(get_collection_page),
):
    items, total = list_review_sets(
        db, project_id, state=state, limit=page.limit, offset=page.offset
    )
    return {
        "items": [review_set_response(item) for item in items],
        "total": total,
        "limit": page.limit,
        "offset": page.offset,
    }


@router.get("/review-sets/{review_set_id}", response_model=ReviewSetResponse)
def get_review_set_route(
    project_id: int,
    review_set_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return review_set_response(get_review_set(db, project_id, review_set_id))


@router.put("/review-sets/{review_set_id}", response_model=ReviewSetResponse)
def update_review_set_route(
    project_id: int,
    review_set_id: PositiveId,
    payload: ReviewSetUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    review_set = get_review_set(db, project_id, review_set_id)
    return review_set_response(update_review_set(db, review_set, payload))


@router.post("/review-sets/{review_set_id}/archive", response_model=ReviewSetResponse)
def archive_review_set_route(
    project_id: int,
    review_set_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return review_set_response(
        archive_review_set(db, get_review_set(db, project_id, review_set_id))
    )


@router.post(
    "/review-sets/{review_set_id}/sources",
    response_model=ReviewSourceResponse,
    status_code=201,
)
def add_review_source_route(
    project_id: int,
    review_set_id: PositiveId,
    payload: ReviewSourceCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    config: PreconstructionAIConfig = Depends(get_preconstruction_config),
    preparation_config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    review_set = get_review_set(db, project_id, review_set_id)
    source = add_review_source(
        db, project_id, review_set, current_user["id"], payload, config
    )
    state = source_preparation_states(db, [source], preparation_config)[source.id]
    return source_response(source, state)


@router.get(
    "/review-sets/{review_set_id}/sources",
    response_model=ReviewSourceListResponse,
)
def list_review_sources_route(
    project_id: int,
    review_set_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    preparation_config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    get_review_set(db, project_id, review_set_id)
    sources = list_review_sources(db, project_id, review_set_id)
    states = source_preparation_states(db, sources, preparation_config)
    return {
        "items": [
            source_response(item, states[item.id])
            for item in sources
        ],
        "roles": [role.__dict__ for role in DOCUMENT_ROLES],
    }


@router.put(
    "/review-sets/{review_set_id}/sources/{source_id}",
    response_model=ReviewSourceResponse,
)
def update_review_source_route(
    project_id: int,
    review_set_id: PositiveId,
    source_id: PositiveId,
    payload: ReviewSourceUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    preparation_config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    review_set = get_review_set(db, project_id, review_set_id)
    source = get_review_source(db, project_id, review_set_id, source_id)
    updated = update_review_source(db, review_set, source, payload)
    state = source_preparation_states(db, [updated], preparation_config)[updated.id]
    return source_response(updated, state)


@router.delete(
    "/review-sets/{review_set_id}/sources/{source_id}",
    response_model=MessageResponse,
)
def remove_review_source_route(
    project_id: int,
    review_set_id: PositiveId,
    source_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    review_set = get_review_set(db, project_id, review_set_id)
    source = get_review_source(db, project_id, review_set_id, source_id)
    remove_review_source(db, review_set, source)
    return {"message": "Preconstruction review source removed"}


@router.get("/source-candidates", response_model=SourceCandidateListResponse)
def source_candidates_route(
    project_id: int,
    source_type: Literal["document", "drawing_revision"],
    search: Annotated[str, Query(max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {
        "items": list_source_candidates(
            db,
            project_id,
            source_type=source_type,
            search=search.strip(),
            limit=limit,
        ),
        "limit": limit,
    }


@router.get(
    "/review-sets/{review_set_id}/readiness",
    response_model=ReadinessResponse,
)
def readiness_route(
    project_id: int,
    review_set_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    config: PreconstructionAIConfig = Depends(get_preconstruction_config),
    provider: PreconstructionAIProvider = Depends(get_preconstruction_provider),
    analysis_type: Annotated[
        Literal[
            "readiness_probe",
            "provider_contract_validation",
            "content_contract_validation",
        ],
        Query(),
    ] = "provider_contract_validation",
    preparation_config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    return review_readiness(
        db,
        get_review_set(db, project_id, review_set_id),
        config,
        provider,
        analysis_type=analysis_type,
        preparation_config=preparation_config,
    )


@router.post(
    "/review-sets/{review_set_id}/runs",
    response_model=AnalysisRunResponse,
    status_code=201,
)
def create_analysis_run_route(
    project_id: int,
    review_set_id: PositiveId,
    payload: AnalysisRunCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    config: PreconstructionAIConfig = Depends(get_preconstruction_config),
    provider: PreconstructionAIProvider = Depends(get_preconstruction_provider),
    preparation_config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    review_set = get_review_set(db, project_id, review_set_id)
    return run_response(
        create_analysis_run(
            db,
            review_set,
            current_user["id"],
            payload,
            config,
            provider,
            preparation_config,
        )
    )


@router.post(
    "/review-sets/{review_set_id}/sources/{source_id}/prepare",
    response_model=PreparationRunResponse,
    status_code=202,
)
def prepare_source_route(
    project_id: int,
    review_set_id: PositiveId,
    source_id: PositiveId,
    payload: PreparationRequest | None = None,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    review_set = get_review_set(db, project_id, review_set_id)
    source = get_preparation_source(db, project_id, review_set_id, source_id)
    run = request_source_preparation(
        db, review_set, source, current_user["id"], config
    )
    return preparation_run_response(db, run)


@router.get(
    "/preparation-runs/{run_id}",
    response_model=PreparationRunResponse,
)
def preparation_run_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return preparation_run_response(db, get_preparation_run(db, project_id, run_id))


@router.post(
    "/preparation-runs/{run_id}/cancel",
    response_model=PreparationRunResponse,
)
def cancel_preparation_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    run = cancel_preparation_run(db, get_preparation_run(db, project_id, run_id))
    return preparation_run_response(db, run)


@router.post(
    "/preparation-runs/{run_id}/retry",
    response_model=PreparationRunResponse,
)
def retry_preparation_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    run = retry_preparation_run(db, get_preparation_run(db, project_id, run_id))
    return preparation_run_response(db, run)


@router.get(
    "/review-sets/{review_set_id}/sources/{source_id}/content",
    response_model=ContentInspectionResponse,
)
def inspect_source_content_route(
    project_id: int,
    review_set_id: PositiveId,
    source_id: PositiveId,
    response: Response,
    snapshot_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    page: Annotated[int | None, Query(ge=1, le=2_000)] = None,
    segment_offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    segment_limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    search: Annotated[str, Query(max_length=200)] = "",
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    config: PreconstructionPreparationConfig = Depends(
        get_preconstruction_preparation_config
    ),
):
    get_review_set(db, project_id, review_set_id)
    source = get_preparation_source(db, project_id, review_set_id, source_id)
    response.headers["Cache-Control"] = "no-store"
    return inspect_source_content(
        db,
        source,
        config,
        snapshot_id=snapshot_id,
        page_number=page,
        segment_offset=segment_offset,
        segment_limit=segment_limit or config.content_page_size,
        search=search,
    )


@router.get(
    "/review-sets/{review_set_id}/runs",
    response_model=AnalysisRunListResponse,
)
def list_analysis_runs_route(
    project_id: int,
    review_set_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    page: CollectionPage = Depends(get_collection_page),
):
    get_review_set(db, project_id, review_set_id)
    items, total = list_analysis_runs(
        db, project_id, review_set_id, limit=page.limit, offset=page.offset
    )
    return {
        "items": [run_response(item) for item in items],
        "total": total,
        "limit": page.limit,
        "offset": page.offset,
    }


@router.get("/runs/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return run_response(get_analysis_run(db, project_id, run_id))


@router.post("/runs/{run_id}/cancel", response_model=AnalysisRunResponse)
def cancel_analysis_run_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return run_response(
        cancel_analysis_run(db, get_analysis_run(db, project_id, run_id))
    )


@router.post("/runs/{run_id}/retry", response_model=AnalysisRunResponse)
def retry_analysis_run_route(
    project_id: int,
    run_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    provider: PreconstructionAIProvider = Depends(get_preconstruction_provider),
):
    return run_response(
        retry_analysis_run(db, get_analysis_run(db, project_id, run_id), provider)
    )
