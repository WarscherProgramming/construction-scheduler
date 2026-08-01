from typing import Annotated, Literal, TypeVar

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    PositiveId,
    get_db,
    get_owned_project,
    get_storage_config,
    get_storage_provider,
    get_storage_provider_resolver,
)
from app.core.config import AttachmentConfig
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.drawing import (
    DrawingDiscipline,
    DrawingIssueCreate,
    DrawingIssueListResponse,
    DrawingIssueMembershipCreate,
    DrawingIssueResponse,
    DrawingIssueUpdate,
    DrawingRegisterResponse,
    DrawingRevisionCreateMetadata,
    DrawingRevisionListResponse,
    DrawingRevisionResponse,
    DrawingSetCreate,
    DrawingSetListResponse,
    DrawingSetResponse,
    DrawingSetUpdate,
    DrawingSheetCreateMetadata,
    DrawingSheetListResponse,
    DrawingSheetResponse,
    DrawingSheetStatus,
    DrawingSheetUpdate,
)
from app.services.document import (
    document_content_disposition,
    get_owned_document,
    open_document_stream,
)
from app.services.drawing import (
    add_issue_revision,
    archive_drawing_set,
    archive_drawing_sheet,
    create_drawing_issue,
    create_drawing_revision,
    create_drawing_set,
    create_sheet_with_revision,
    delete_draft_issue,
    drawing_set_response,
    get_drawing_register,
    get_owned_drawing_issue,
    get_owned_drawing_revision,
    get_owned_drawing_set,
    get_owned_drawing_sheet,
    issue_drawing_issue,
    issue_response,
    list_drawing_issues,
    list_drawing_revisions,
    list_drawing_sets,
    list_drawing_sheets,
    remove_issue_revision,
    revision_response,
    sheet_response,
    update_drawing_issue,
    update_drawing_set,
    update_drawing_sheet,
    void_drawing_issue,
)
from app.storage.provider import StorageProvider


router = APIRouter()
MetadataModel = TypeVar("MetadataModel", bound=BaseModel)
DrawingSort = Literal[
    "sheet_number",
    "title",
    "discipline",
    "revision_date",
    "updated_at",
]
SortOrder = Literal["asc", "desc"]


def parse_multipart_metadata(
    value: str,
    model: type[MetadataModel],
) -> MetadataModel:
    try:
        return model.model_validate_json(value)
    except ValidationError as error:
        detail = [
            {
                "type": item["type"],
                "loc": ["body", "metadata", *item["loc"]],
                "msg": item["msg"],
            }
            for item in error.errors()
        ]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        ) from error


@router.get(
    "/projects/{project_id}/drawing-sets",
    response_model=DrawingSetListResponse,
)
def get_project_drawing_sets(
    project_id: int,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {
        "drawing_sets": list_drawing_sets(
            db,
            project_id,
            include_archived=include_archived,
        )
    }


@router.post(
    "/projects/{project_id}/drawing-sets",
    response_model=DrawingSetResponse,
    status_code=201,
)
def post_drawing_set(
    project_id: int,
    payload: DrawingSetCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return create_drawing_set(db, project_id, current_user["id"], payload)


@router.get(
    "/drawing-sets/{drawing_set_id}",
    response_model=DrawingSetResponse,
)
def get_drawing_set(
    drawing_set_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db, drawing_set_id, current_user["id"]
    )
    return drawing_set_response(db, drawing_set)


@router.patch(
    "/drawing-sets/{drawing_set_id}",
    response_model=DrawingSetResponse,
)
def patch_drawing_set(
    drawing_set_id: PositiveId,
    payload: DrawingSetUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db, drawing_set_id, current_user["id"]
    )
    return update_drawing_set(db, drawing_set, payload)


@router.delete(
    "/drawing-sets/{drawing_set_id}",
    response_model=DrawingSetResponse,
)
def delete_drawing_set(
    drawing_set_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db, drawing_set_id, current_user["id"]
    )
    return archive_drawing_set(db, drawing_set)


@router.get(
    "/drawing-sets/{drawing_set_id}/sheets",
    response_model=DrawingSheetListResponse,
)
def get_drawing_set_sheets(
    drawing_set_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db, drawing_set_id, current_user["id"]
    )
    return {"sheets": list_drawing_sheets(db, drawing_set)}


@router.post(
    "/drawing-sets/{drawing_set_id}/sheets",
    response_model=DrawingSheetResponse,
    status_code=201,
)
def post_drawing_sheet(
    drawing_set_id: PositiveId,
    metadata: str = Form(..., max_length=25_000),
    file: UploadFile = File(...),
    content_length: int | None = Header(
        default=None,
        alias="Content-Length",
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
    config: AttachmentConfig = Depends(get_storage_config),
):
    drawing_set = get_owned_drawing_set(
        db,
        drawing_set_id,
        current_user["id"],
        include_archived=False,
    )
    parsed = parse_multipart_metadata(
        metadata,
        DrawingSheetCreateMetadata,
    )
    return create_sheet_with_revision(
        db,
        storage,
        config,
        drawing_set,
        current_user["id"],
        parsed,
        file,
        content_length,
    )


@router.get(
    "/drawing-sheets/{sheet_id}",
    response_model=DrawingSheetResponse,
)
def get_drawing_sheet(
    sheet_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sheet = get_owned_drawing_sheet(db, sheet_id, current_user["id"])
    return sheet_response(db, sheet)


@router.patch(
    "/drawing-sheets/{sheet_id}",
    response_model=DrawingSheetResponse,
)
def patch_drawing_sheet(
    sheet_id: PositiveId,
    payload: DrawingSheetUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sheet = get_owned_drawing_sheet(db, sheet_id, current_user["id"])
    return update_drawing_sheet(db, sheet, payload)


@router.delete(
    "/drawing-sheets/{sheet_id}",
    response_model=DrawingSheetResponse,
)
def delete_drawing_sheet(
    sheet_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sheet = get_owned_drawing_sheet(db, sheet_id, current_user["id"])
    return archive_drawing_sheet(db, sheet)


@router.get(
    "/drawing-sheets/{sheet_id}/revisions",
    response_model=DrawingRevisionListResponse,
)
def get_sheet_revisions(
    sheet_id: PositiveId,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sheet = get_owned_drawing_sheet(db, sheet_id, current_user["id"])
    return {
        "revisions": list_drawing_revisions(
            db, sheet, limit=limit, offset=offset
        )
    }


@router.get(
    "/drawing-sheets/{sheet_id}/current-revision",
    response_model=DrawingRevisionResponse,
)
def get_sheet_current_revision(
    sheet_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sheet = get_owned_drawing_sheet(db, sheet_id, current_user["id"])
    if sheet.current_revision_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current drawing revision not found",
        )
    revision = get_owned_drawing_revision(
        db, sheet.current_revision_id, current_user["id"]
    )
    return revision_response(db, revision)


@router.post(
    "/drawing-sheets/{sheet_id}/revisions",
    response_model=DrawingRevisionResponse,
    status_code=201,
)
def post_sheet_revision(
    sheet_id: PositiveId,
    metadata: str = Form(..., max_length=25_000),
    file: UploadFile = File(...),
    content_length: int | None = Header(
        default=None,
        alias="Content-Length",
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
    config: AttachmentConfig = Depends(get_storage_config),
):
    sheet = get_owned_drawing_sheet(
        db, sheet_id, current_user["id"], include_archived=False
    )
    parsed = parse_multipart_metadata(
        metadata,
        DrawingRevisionCreateMetadata,
    )
    return create_drawing_revision(
        db,
        storage,
        config,
        sheet,
        current_user["id"],
        parsed,
        file,
        content_length,
    )


@router.get("/drawing-revisions/{revision_id}/download")
def download_drawing_revision(
    revision_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    storage_resolver=Depends(get_storage_provider_resolver),
    config: AttachmentConfig = Depends(get_storage_config),
):
    revision = get_owned_drawing_revision(
        db, revision_id, current_user["id"]
    )
    document = get_owned_document(
        db, revision.document_id, current_user["id"]
    )
    content = open_document_stream(
        storage_resolver, document, config.upload_chunk_size
    )
    return StreamingResponse(
        content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": document_content_disposition(document),
            "Content-Length": str(document.size_bytes),
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/drawing-sets/{drawing_set_id}/issues",
    response_model=DrawingIssueListResponse,
)
def get_drawing_set_issues(
    drawing_set_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db, drawing_set_id, current_user["id"]
    )
    return {"issues": list_drawing_issues(db, drawing_set)}


@router.post(
    "/drawing-sets/{drawing_set_id}/issues",
    response_model=DrawingIssueResponse,
    status_code=201,
)
def post_drawing_issue(
    drawing_set_id: PositiveId,
    payload: DrawingIssueCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    drawing_set = get_owned_drawing_set(
        db,
        drawing_set_id,
        current_user["id"],
        include_archived=False,
    )
    return create_drawing_issue(
        db, drawing_set, current_user["id"], payload
    )


@router.get(
    "/drawing-issues/{issue_id}",
    response_model=DrawingIssueResponse,
)
def get_drawing_issue(
    issue_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(db, issue_id, current_user["id"])
    return issue_response(db, issue)


@router.patch(
    "/drawing-issues/{issue_id}",
    response_model=DrawingIssueResponse,
)
def patch_drawing_issue(
    issue_id: PositiveId,
    payload: DrawingIssueUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    return update_drawing_issue(db, issue, payload)


@router.delete(
    "/drawing-issues/{issue_id}",
    response_model=DrawingIssueResponse,
)
def delete_drawing_issue(
    issue_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    return delete_draft_issue(db, issue)


@router.post(
    "/drawing-issues/{issue_id}/revisions",
    response_model=DrawingIssueResponse,
)
def post_issue_revision(
    issue_id: PositiveId,
    payload: DrawingIssueMembershipCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    revision = get_owned_drawing_revision(
        db, payload.revision_id, current_user["id"]
    )
    return add_issue_revision(db, issue, revision)


@router.delete(
    "/drawing-issues/{issue_id}/revisions/{revision_id}",
    response_model=DrawingIssueResponse,
)
def delete_issue_revision(
    issue_id: PositiveId,
    revision_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    return remove_issue_revision(db, issue, revision_id)


@router.post(
    "/drawing-issues/{issue_id}/issue",
    response_model=DrawingIssueResponse,
)
def post_issue_drawing_issue(
    issue_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    return issue_drawing_issue(db, issue)


@router.post(
    "/drawing-issues/{issue_id}/void",
    response_model=DrawingIssueResponse,
)
def post_void_drawing_issue(
    issue_id: PositiveId,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    issue = get_owned_drawing_issue(
        db, issue_id, current_user["id"], include_deleted=False
    )
    return void_drawing_issue(db, issue)


@router.get(
    "/projects/{project_id}/drawings",
    response_model=DrawingRegisterResponse,
)
def get_project_drawing_register(
    project_id: int,
    drawing_set_id: Annotated[
        int | None, Query(ge=1, le=2_147_483_647)
    ] = None,
    discipline: DrawingDiscipline | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sheet_status: DrawingSheetStatus | None = None,
    sort: DrawingSort = "sheet_number",
    order: SortOrder = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return get_drawing_register(
        db,
        project_id,
        drawing_set_id=drawing_set_id,
        discipline=discipline,
        search=search,
        sheet_status=sheet_status,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
