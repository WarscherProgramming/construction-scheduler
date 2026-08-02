from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    PositiveId,
    get_db,
    get_document_extraction_config,
    get_owned_project,
)
from app.core.config import DocumentExtractionConfig
from app.core.rate_limit import InMemoryRateLimiter, rate_limit_key
from app.core.security import get_current_user
from app.models.document import Document
from app.models.project import Project
from app.schemas.document_search import (
    DocumentExtractionReprocessRequest,
    DocumentExtractionStatusResponse,
    DocumentSearchResponse,
)
from app.schemas.drawing import DrawingDiscipline
from app.services.document import get_owned_document
from app.services.document_extraction import (
    get_document_extraction_summary,
    reprocess_document_extraction,
)
from app.services.document_search import search_project_documents


router = APIRouter()
SearchScope = Literal["all", "documents", "drawings"]
ExtractionMethodFilter = Literal[
    "embedded_text",
    "ocr",
    "mixed",
    "metadata_only",
    "unavailable",
]
reprocess_rate_limiter = InMemoryRateLimiter(max_entries=10_000)


def _project_document(
    db: Session,
    project_id: int,
    document_id: int,
    user_id: int,
) -> Document:
    document = get_owned_document(db, document_id, user_id)
    if document.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.get(
    "/projects/{project_id}/documents/{document_id}/extraction",
    response_model=DocumentExtractionStatusResponse,
)
def get_document_extraction_status(
    project_id: PositiveId,
    document_id: PositiveId,
    response: Response,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    config: DocumentExtractionConfig = Depends(
        get_document_extraction_config
    ),
):
    response.headers["Cache-Control"] = "no-store"
    document = _project_document(
        db,
        project_id,
        document_id,
        current_user["id"],
    )
    return {
        "project_id": project_id,
        "document_id": document.id,
        "extraction": get_document_extraction_summary(
            db,
            document,
            config,
        ),
    }


@router.post(
    "/projects/{project_id}/documents/{document_id}/extraction/reprocess",
    response_model=DocumentExtractionStatusResponse,
    status_code=202,
)
def reprocess_document_text(
    project_id: PositiveId,
    document_id: PositiveId,
    payload: DocumentExtractionReprocessRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
    config: DocumentExtractionConfig = Depends(
        get_document_extraction_config
    ),
):
    response.headers["Cache-Control"] = "no-store"
    client_host = request.client.host if request.client else "unknown"
    key = rate_limit_key(
        "document-extraction-reprocess",
        client_host,
        f"{current_user['id']}:{project_id}",
    )
    rate_result = reprocess_rate_limiter.consume(
        key,
        limit=config.reprocess_rate_limit,
        window_seconds=config.reprocess_rate_window_seconds,
    )
    if not rate_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many document reprocessing requests",
            headers={"Retry-After": str(rate_result.retry_after)},
        )
    document = _project_document(
        db,
        project_id,
        document_id,
        current_user["id"],
    )
    extraction = reprocess_document_extraction(
        db,
        document,
        current_user["id"],
        config,
    )
    return {
        "project_id": project_id,
        "document_id": document.id,
        "extraction": extraction,
    }


@router.get(
    "/projects/{project_id}/search",
    response_model=DocumentSearchResponse,
)
def search_project_document_content(
    project_id: PositiveId,
    response: Response,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    scope: SearchScope = "all",
    document_type: Annotated[str | None, Query(max_length=50)] = None,
    drawing_set_id: Annotated[
        int | None,
        Query(ge=1, le=2_147_483_647),
    ] = None,
    discipline: DrawingDiscipline | None = None,
    current_revisions_only: bool = True,
    extraction_method: ExtractionMethodFilter | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    response.headers["Cache-Control"] = "no-store"
    return search_project_documents(
        db,
        project_id,
        q=q,
        scope=scope,
        document_type=document_type,
        drawing_set_id=drawing_set_id,
        discipline=discipline,
        current_revisions_only=current_revisions_only,
        extraction_method=extraction_method,
        limit=limit,
        offset=offset,
    )
