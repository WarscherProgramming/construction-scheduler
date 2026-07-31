from datetime import datetime, timezone
from pathlib import Path
import re
import unicodedata

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import AttachmentConfig
from app.models.document import Document
from app.models.drawing import (
    DrawingIssue,
    DrawingIssueRevision,
    DrawingRevision,
    DrawingSet,
    DrawingSheet,
)
from app.models.project import Project
from app.schemas.drawing import (
    DrawingIssueCreate,
    DrawingIssueUpdate,
    DrawingRevisionCreateMetadata,
    DrawingSetCreate,
    DrawingSetUpdate,
    DrawingSheetCreateMetadata,
    DrawingSheetUpdate,
)
from app.services.document import (
    _cleanup_failed_document_upload,
    create_document,
)
from app.storage.provider import StorageProvider


MAX_SEARCH_LENGTH = 200


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_sheet_number(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).upper()
    normalized = re.sub(r"[\s-]+", "", normalized)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid sheet number is required",
        )
    return normalized


def normalize_revision_code(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    normalized = re.sub(r"\s+", "", normalized)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid revision code is required",
        )
    return normalized


def drawing_sort_key(sheet_number: str) -> str:
    normalized = normalize_sheet_number(sheet_number)
    return re.sub(
        r"\d+",
        lambda match: match.group(0).zfill(12),
        normalized,
    )


def _not_found(resource: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found",
    )


def get_owned_drawing_set(
    db: Session,
    drawing_set_id: int,
    user_id: int,
    *,
    include_archived: bool = True,
) -> DrawingSet:
    query = (
        db.query(DrawingSet)
        .join(Project, Project.id == DrawingSet.project_id)
        .filter(
            DrawingSet.id == drawing_set_id,
            Project.user_id == user_id,
        )
    )
    if not include_archived:
        query = query.filter(DrawingSet.deleted_at.is_(None))
    drawing_set = query.first()
    if drawing_set is None:
        raise _not_found("Drawing set")
    return drawing_set


def get_owned_drawing_sheet(
    db: Session,
    sheet_id: int,
    user_id: int,
    *,
    include_archived: bool = True,
) -> DrawingSheet:
    query = (
        db.query(DrawingSheet)
        .join(Project, Project.id == DrawingSheet.project_id)
        .filter(
            DrawingSheet.id == sheet_id,
            Project.user_id == user_id,
        )
    )
    if not include_archived:
        query = query.filter(DrawingSheet.deleted_at.is_(None))
    sheet = query.first()
    if sheet is None:
        raise _not_found("Drawing sheet")
    return sheet


def get_owned_drawing_revision(
    db: Session,
    revision_id: int,
    user_id: int,
) -> DrawingRevision:
    revision = (
        db.query(DrawingRevision)
        .join(Project, Project.id == DrawingRevision.project_id)
        .filter(
            DrawingRevision.id == revision_id,
            Project.user_id == user_id,
        )
        .first()
    )
    if revision is None:
        raise _not_found("Drawing revision")
    return revision


def get_owned_drawing_issue(
    db: Session,
    issue_id: int,
    user_id: int,
    *,
    include_deleted: bool = True,
) -> DrawingIssue:
    query = (
        db.query(DrawingIssue)
        .join(Project, Project.id == DrawingIssue.project_id)
        .filter(
            DrawingIssue.id == issue_id,
            Project.user_id == user_id,
        )
    )
    if not include_deleted:
        query = query.filter(DrawingIssue.deleted_at.is_(None))
    issue = query.first()
    if issue is None:
        raise _not_found("Drawing issue")
    return issue


def _set_responses(db: Session, drawing_sets: list[DrawingSet]) -> list[dict]:
    if not drawing_sets:
        return []
    set_ids = [drawing_set.id for drawing_set in drawing_sets]
    sheet_counts = dict(
        db.query(DrawingSheet.drawing_set_id, func.count(DrawingSheet.id))
        .filter(
            DrawingSheet.drawing_set_id.in_(set_ids),
            DrawingSheet.deleted_at.is_(None),
        )
        .group_by(DrawingSheet.drawing_set_id)
        .all()
    )
    issue_counts = dict(
        db.query(DrawingIssue.drawing_set_id, func.count(DrawingIssue.id))
        .filter(
            DrawingIssue.drawing_set_id.in_(set_ids),
            DrawingIssue.deleted_at.is_(None),
        )
        .group_by(DrawingIssue.drawing_set_id)
        .all()
    )
    return [
        {
            "id": item.id,
            "project_id": item.project_id,
            "name": item.name,
            "description": item.description,
            "status": item.status,
            "issue_date": item.issue_date,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "deleted_at": item.deleted_at,
            "sheet_count": sheet_counts.get(item.id, 0),
            "issue_count": issue_counts.get(item.id, 0),
        }
        for item in drawing_sets
    ]


def drawing_set_response(db: Session, drawing_set: DrawingSet) -> dict:
    return _set_responses(db, [drawing_set])[0]


def list_drawing_sets(
    db: Session,
    project_id: int,
    *,
    include_archived: bool = False,
) -> list[dict]:
    query = db.query(DrawingSet).filter(
        DrawingSet.project_id == project_id,
    )
    if not include_archived:
        query = query.filter(DrawingSet.deleted_at.is_(None))
    drawing_sets = query.order_by(
        func.lower(DrawingSet.name).asc(),
        DrawingSet.id.asc(),
    ).all()
    return _set_responses(db, drawing_sets)


def create_drawing_set(
    db: Session,
    project_id: int,
    user_id: int,
    payload: DrawingSetCreate,
) -> dict:
    drawing_set = DrawingSet(
        project_id=project_id,
        created_by=user_id,
        **payload.model_dump(),
    )
    db.add(drawing_set)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active drawing set with this name already exists",
        ) from error
    db.refresh(drawing_set)
    return drawing_set_response(db, drawing_set)


def update_drawing_set(
    db: Session,
    drawing_set: DrawingSet,
    payload: DrawingSetUpdate,
) -> dict:
    if drawing_set.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived drawing sets cannot be edited",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(drawing_set, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active drawing set with this name already exists",
        ) from error
    db.refresh(drawing_set)
    return drawing_set_response(db, drawing_set)


def archive_drawing_set(db: Session, drawing_set: DrawingSet) -> dict:
    if drawing_set.deleted_at is None:
        drawing_set.status = "archived"
        drawing_set.deleted_at = utc_now()
        db.commit()
        db.refresh(drawing_set)
    return drawing_set_response(db, drawing_set)


def _revision_responses(
    db: Session,
    revisions: list[DrawingRevision],
) -> list[dict]:
    if not revisions:
        return []
    document_ids = [revision.document_id for revision in revisions]
    revision_ids = [revision.id for revision in revisions]
    documents = {
        document.id: document
        for document in db.query(Document)
        .filter(Document.id.in_(document_ids))
        .all()
    }
    memberships: dict[int, list[int]] = {}
    for revision_id, issue_id in (
        db.query(
            DrawingIssueRevision.drawing_revision_id,
            DrawingIssueRevision.drawing_issue_id,
        )
        .filter(DrawingIssueRevision.drawing_revision_id.in_(revision_ids))
        .order_by(DrawingIssueRevision.drawing_issue_id.asc())
        .all()
    ):
        memberships.setdefault(revision_id, []).append(issue_id)
    responses = []
    for revision in revisions:
        document = documents[revision.document_id]
        responses.append(
            {
                "id": revision.id,
                "project_id": revision.project_id,
                "drawing_sheet_id": revision.drawing_sheet_id,
                "document_id": revision.document_id,
                "revision_code": revision.revision_code,
                "revision_date": revision.revision_date,
                "description": revision.description,
                "sequence_number": revision.sequence_number,
                "is_current": revision.is_current,
                "superseded_at": revision.superseded_at,
                "superseded_by_revision_id": (
                    revision.superseded_by_revision_id
                ),
                "original_filename": document.original_filename,
                "size_bytes": document.size_bytes,
                "created_at": revision.created_at,
                "issue_ids": memberships.get(revision.id, []),
            }
        )
    return responses


def revision_response(db: Session, revision: DrawingRevision) -> dict:
    return _revision_responses(db, [revision])[0]


def _sheet_responses(db: Session, sheets: list[DrawingSheet]) -> list[dict]:
    if not sheets:
        return []
    sheet_ids = [sheet.id for sheet in sheets]
    set_ids = {sheet.drawing_set_id for sheet in sheets}
    sets = {
        item.id: item
        for item in db.query(DrawingSet)
        .filter(DrawingSet.id.in_(set_ids))
        .all()
    }
    revision_counts = dict(
        db.query(
            DrawingRevision.drawing_sheet_id,
            func.count(DrawingRevision.id),
        )
        .filter(DrawingRevision.drawing_sheet_id.in_(sheet_ids))
        .group_by(DrawingRevision.drawing_sheet_id)
        .all()
    )
    current_ids = [
        sheet.current_revision_id
        for sheet in sheets
        if sheet.current_revision_id is not None
    ]
    current_revisions = (
        db.query(DrawingRevision)
        .filter(DrawingRevision.id.in_(current_ids))
        .all()
        if current_ids
        else []
    )
    current_responses = {
        response["id"]: response
        for response in _revision_responses(db, current_revisions)
    }
    return [
        {
            "id": sheet.id,
            "project_id": sheet.project_id,
            "drawing_set_id": sheet.drawing_set_id,
            "drawing_set_name": sets[sheet.drawing_set_id].name,
            "sheet_number": sheet.sheet_number,
            "title": sheet.title,
            "discipline": sheet.discipline,
            "description": sheet.description,
            "status": sheet.status,
            "current_revision_id": sheet.current_revision_id,
            "current_revision": current_responses.get(
                sheet.current_revision_id
            ),
            "revision_count": revision_counts.get(sheet.id, 0),
            "created_at": sheet.created_at,
            "updated_at": sheet.updated_at,
            "deleted_at": sheet.deleted_at,
        }
        for sheet in sheets
    ]


def sheet_response(db: Session, sheet: DrawingSheet) -> dict:
    return _sheet_responses(db, [sheet])[0]


def list_drawing_sheets(
    db: Session,
    drawing_set: DrawingSet,
) -> list[dict]:
    sheets = (
        db.query(DrawingSheet)
        .filter(
            DrawingSheet.drawing_set_id == drawing_set.id,
            DrawingSheet.deleted_at.is_(None),
        )
        .order_by(DrawingSheet.sort_key.asc(), DrawingSheet.id.asc())
        .all()
    )
    return _sheet_responses(db, sheets)


def _cleanup_drawing_upload(
    db: Session,
    storage: StorageProvider,
    document: Document | None,
) -> None:
    if document is None:
        return
    _cleanup_failed_document_upload(
        db,
        storage,
        document.project_id,
        document.storage_key,
    )


def _assert_active_set(drawing_set: DrawingSet) -> None:
    if drawing_set.deleted_at is not None or drawing_set.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived drawing sets cannot be changed",
        )


def _validate_drawing_pdf(upload: UploadFile) -> None:
    if Path(upload.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Drawing revisions must be PDF files",
        )


def create_sheet_with_revision(
    db: Session,
    storage: StorageProvider,
    config: AttachmentConfig,
    drawing_set: DrawingSet,
    user_id: int,
    metadata: DrawingSheetCreateMetadata,
    upload: UploadFile,
    content_length: int | None,
) -> dict:
    _assert_active_set(drawing_set)
    _validate_drawing_pdf(upload)
    db.query(DrawingSet).filter(
        DrawingSet.id == drawing_set.id
    ).with_for_update().one()
    normalized_number = normalize_sheet_number(metadata.sheet_number)
    duplicate = (
        db.query(DrawingSheet.id)
        .filter(
            DrawingSheet.drawing_set_id == drawing_set.id,
            DrawingSheet.normalized_sheet_number == normalized_number,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sheet with this number already exists in the set",
        )

    sheet = DrawingSheet(
        project_id=drawing_set.project_id,
        drawing_set_id=drawing_set.id,
        sheet_number=metadata.sheet_number,
        normalized_sheet_number=normalized_number,
        title=metadata.title,
        discipline=metadata.discipline,
        description=metadata.description,
        sort_key=drawing_sort_key(metadata.sheet_number),
        status="active",
        created_by=user_id,
    )
    db.add(sheet)
    document = None
    try:
        db.flush()
        document = create_document(
            db,
            storage,
            config,
            project_id=drawing_set.project_id,
            folder_id=None,
            upload=upload,
            uploaded_by=user_id,
            display_name=(
                f"{metadata.sheet_number} - {metadata.title} - "
                f"Rev {metadata.revision_code}"
            ),
            document_type="Drawing",
            content_length=content_length,
            commit=False,
        )
        revision = DrawingRevision(
            project_id=drawing_set.project_id,
            drawing_sheet_id=sheet.id,
            document_id=document.id,
            revision_code=metadata.revision_code,
            normalized_revision_code=normalize_revision_code(
                metadata.revision_code
            ),
            revision_date=metadata.revision_date,
            description=metadata.revision_description,
            sequence_number=1,
            is_current=True,
            uploaded_by=user_id,
        )
        db.add(revision)
        db.flush()
        sheet.current_revision_id = revision.id
        db.commit()
    except HTTPException:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise
    except IntegrityError as error:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drawing sheet or revision already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create drawing sheet",
        ) from error
    db.refresh(sheet)
    return sheet_response(db, sheet)


def update_drawing_sheet(
    db: Session,
    sheet: DrawingSheet,
    payload: DrawingSheetUpdate,
) -> dict:
    if sheet.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived drawing sheets cannot be edited",
        )
    values = payload.model_dump(exclude_unset=True)
    if "sheet_number" in values:
        values["normalized_sheet_number"] = normalize_sheet_number(
            values["sheet_number"]
        )
        values["sort_key"] = drawing_sort_key(values["sheet_number"])
    for field, value in values.items():
        setattr(sheet, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sheet with this number already exists in the set",
        ) from error
    db.refresh(sheet)
    return sheet_response(db, sheet)


def archive_drawing_sheet(db: Session, sheet: DrawingSheet) -> dict:
    if sheet.deleted_at is None:
        sheet.status = "archived"
        sheet.deleted_at = utc_now()
        db.commit()
        db.refresh(sheet)
    return sheet_response(db, sheet)


def create_drawing_revision(
    db: Session,
    storage: StorageProvider,
    config: AttachmentConfig,
    sheet: DrawingSheet,
    user_id: int,
    metadata: DrawingRevisionCreateMetadata,
    upload: UploadFile,
    content_length: int | None,
) -> dict:
    if sheet.deleted_at is not None or sheet.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active drawing sheets accept revisions",
        )
    _validate_drawing_pdf(upload)
    sheet = (
        db.query(DrawingSheet)
        .filter(DrawingSheet.id == sheet.id)
        .with_for_update()
        .one()
    )
    normalized_code = normalize_revision_code(metadata.revision_code)
    duplicate = (
        db.query(DrawingRevision.id)
        .filter(
            DrawingRevision.drawing_sheet_id == sheet.id,
            DrawingRevision.normalized_revision_code == normalized_code,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This revision code already exists for the sheet",
        )
    previous = (
        db.query(DrawingRevision)
        .filter(DrawingRevision.id == sheet.current_revision_id)
        .with_for_update()
        .first()
    )
    next_sequence = (
        db.query(func.max(DrawingRevision.sequence_number))
        .filter(DrawingRevision.drawing_sheet_id == sheet.id)
        .scalar()
        or 0
    ) + 1
    document = None
    try:
        document = create_document(
            db,
            storage,
            config,
            project_id=sheet.project_id,
            folder_id=None,
            upload=upload,
            uploaded_by=user_id,
            display_name=(
                f"{sheet.sheet_number} - {sheet.title} - "
                f"Rev {metadata.revision_code}"
            ),
            document_type="Drawing",
            content_length=content_length,
            commit=False,
        )
        revision = DrawingRevision(
            project_id=sheet.project_id,
            drawing_sheet_id=sheet.id,
            document_id=document.id,
            revision_code=metadata.revision_code,
            normalized_revision_code=normalized_code,
            revision_date=metadata.revision_date,
            description=metadata.description,
            sequence_number=next_sequence,
            is_current=True,
            uploaded_by=user_id,
        )
        if previous is not None:
            previous.is_current = False
            previous.superseded_at = utc_now()
            db.flush()
        db.add(revision)
        db.flush()
        if previous is not None:
            previous.superseded_by_revision_id = revision.id
        sheet.current_revision_id = revision.id
        db.commit()
    except HTTPException:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise
    except IntegrityError as error:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drawing revision already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        _cleanup_drawing_upload(db, storage, document)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create drawing revision",
        ) from error
    db.refresh(revision)
    return revision_response(db, revision)


def list_drawing_revisions(
    db: Session,
    sheet: DrawingSheet,
    *,
    limit: int,
    offset: int,
) -> list[dict]:
    revisions = (
        db.query(DrawingRevision)
        .filter(DrawingRevision.drawing_sheet_id == sheet.id)
        .order_by(
            DrawingRevision.sequence_number.desc(),
            DrawingRevision.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return _revision_responses(db, revisions)


def _issue_responses(db: Session, issues: list[DrawingIssue]) -> list[dict]:
    if not issues:
        return []
    issue_ids = [issue.id for issue in issues]
    set_ids = {issue.drawing_set_id for issue in issues}
    sets = {
        item.id: item
        for item in db.query(DrawingSet)
        .filter(DrawingSet.id.in_(set_ids))
        .all()
    }
    memberships = (
        db.query(
            DrawingIssueRevision.drawing_issue_id,
            DrawingRevision,
            DrawingSheet,
        )
        .join(
            DrawingRevision,
            DrawingRevision.id
            == DrawingIssueRevision.drawing_revision_id,
        )
        .join(
            DrawingSheet,
            DrawingSheet.id == DrawingRevision.drawing_sheet_id,
        )
        .filter(DrawingIssueRevision.drawing_issue_id.in_(issue_ids))
        .order_by(
            DrawingSheet.sort_key.asc(),
            DrawingRevision.sequence_number.asc(),
        )
        .all()
    )
    member_map: dict[int, list[dict]] = {}
    for issue_id, revision, sheet in memberships:
        member_map.setdefault(issue_id, []).append(
            {
                "revision_id": revision.id,
                "sheet_id": sheet.id,
                "sheet_number": sheet.sheet_number,
                "sheet_title": sheet.title,
                "revision_code": revision.revision_code,
                "revision_date": revision.revision_date,
                "is_current": revision.is_current,
            }
        )
    return [
        {
            "id": issue.id,
            "project_id": issue.project_id,
            "drawing_set_id": issue.drawing_set_id,
            "drawing_set_name": sets[issue.drawing_set_id].name,
            "name": issue.name,
            "issue_number": issue.issue_number,
            "issue_date": issue.issue_date,
            "purpose": issue.purpose,
            "status": issue.status,
            "notes": issue.notes,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "issued_at": issue.issued_at,
            "deleted_at": issue.deleted_at,
            "revisions": member_map.get(issue.id, []),
        }
        for issue in issues
    ]


def issue_response(db: Session, issue: DrawingIssue) -> dict:
    return _issue_responses(db, [issue])[0]


def list_drawing_issues(
    db: Session,
    drawing_set: DrawingSet,
) -> list[dict]:
    issues = (
        db.query(DrawingIssue)
        .filter(
            DrawingIssue.drawing_set_id == drawing_set.id,
            DrawingIssue.deleted_at.is_(None),
        )
        .order_by(
            DrawingIssue.issue_date.desc(),
            DrawingIssue.id.desc(),
        )
        .all()
    )
    return _issue_responses(db, issues)


def create_drawing_issue(
    db: Session,
    drawing_set: DrawingSet,
    user_id: int,
    payload: DrawingIssueCreate,
) -> dict:
    _assert_active_set(drawing_set)
    issue = DrawingIssue(
        project_id=drawing_set.project_id,
        drawing_set_id=drawing_set.id,
        created_by=user_id,
        status="draft",
        **payload.model_dump(),
    )
    db.add(issue)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This issue number already exists in the drawing set",
        ) from error
    db.refresh(issue)
    return issue_response(db, issue)


def _assert_draft_issue(issue: DrawingIssue) -> None:
    if issue.deleted_at is not None or issue.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft issue membership can be changed",
        )


def update_drawing_issue(
    db: Session,
    issue: DrawingIssue,
    payload: DrawingIssueUpdate,
) -> dict:
    _assert_draft_issue(issue)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This issue number already exists in the drawing set",
        ) from error
    db.refresh(issue)
    return issue_response(db, issue)


def add_issue_revision(
    db: Session,
    issue: DrawingIssue,
    revision: DrawingRevision,
) -> dict:
    _assert_draft_issue(issue)
    sheet = db.query(DrawingSheet).filter(
        DrawingSheet.id == revision.drawing_sheet_id
    ).one()
    if (
        revision.project_id != issue.project_id
        or sheet.drawing_set_id != issue.drawing_set_id
    ):
        raise _not_found("Drawing revision")
    existing_sheet = (
        db.query(DrawingIssueRevision)
        .join(
            DrawingRevision,
            DrawingRevision.id
            == DrawingIssueRevision.drawing_revision_id,
        )
        .filter(
            DrawingIssueRevision.drawing_issue_id == issue.id,
            DrawingRevision.drawing_sheet_id == sheet.id,
        )
        .first()
    )
    if existing_sheet is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The issue already contains a revision for this sheet",
        )
    db.add(
        DrawingIssueRevision(
            drawing_issue_id=issue.id,
            drawing_revision_id=revision.id,
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This revision is already included in the issue",
        ) from error
    db.refresh(issue)
    return issue_response(db, issue)


def remove_issue_revision(
    db: Session,
    issue: DrawingIssue,
    revision_id: int,
) -> dict:
    _assert_draft_issue(issue)
    membership = (
        db.query(DrawingIssueRevision)
        .filter(
            DrawingIssueRevision.drawing_issue_id == issue.id,
            DrawingIssueRevision.drawing_revision_id == revision_id,
        )
        .first()
    )
    if membership is None:
        raise _not_found("Issue revision")
    db.delete(membership)
    db.commit()
    db.refresh(issue)
    return issue_response(db, issue)


def issue_drawing_issue(db: Session, issue: DrawingIssue) -> dict:
    if issue.status == "issued":
        return issue_response(db, issue)
    _assert_draft_issue(issue)
    membership_count = (
        db.query(func.count(DrawingIssueRevision.drawing_revision_id))
        .filter(DrawingIssueRevision.drawing_issue_id == issue.id)
        .scalar()
    )
    if membership_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A drawing issue must include at least one revision",
        )
    issue.status = "issued"
    issue.issued_at = utc_now()
    db.commit()
    db.refresh(issue)
    return issue_response(db, issue)


def void_drawing_issue(db: Session, issue: DrawingIssue) -> dict:
    if issue.status == "void":
        return issue_response(db, issue)
    if issue.deleted_at is not None or issue.status != "issued":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an issued drawing issue can be voided",
        )
    issue.status = "void"
    db.commit()
    db.refresh(issue)
    return issue_response(db, issue)


def delete_draft_issue(db: Session, issue: DrawingIssue) -> dict:
    _assert_draft_issue(issue)
    issue.deleted_at = utc_now()
    db.commit()
    db.refresh(issue)
    return issue_response(db, issue)


def get_drawing_register(
    db: Session,
    project_id: int,
    *,
    drawing_set_id: int | None,
    discipline: str | None,
    search: str | None,
    sheet_status: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> dict:
    query = (
        db.query(DrawingSheet)
        .join(DrawingSet, DrawingSet.id == DrawingSheet.drawing_set_id)
        .outerjoin(
            DrawingRevision,
            DrawingRevision.id == DrawingSheet.current_revision_id,
        )
        .filter(
            DrawingSheet.project_id == project_id,
            DrawingSheet.deleted_at.is_(None),
            DrawingSet.deleted_at.is_(None),
        )
    )
    if drawing_set_id is not None:
        owned_set = (
            db.query(DrawingSet.id)
            .filter(
                DrawingSet.id == drawing_set_id,
                DrawingSet.project_id == project_id,
                DrawingSet.deleted_at.is_(None),
            )
            .first()
        )
        if owned_set is None:
            raise _not_found("Drawing set")
        query = query.filter(DrawingSheet.drawing_set_id == drawing_set_id)
    if discipline:
        query = query.filter(DrawingSheet.discipline == discipline)
    if sheet_status:
        query = query.filter(DrawingSheet.status == sheet_status)
    if search is not None:
        normalized_search = unicodedata.normalize("NFKC", search).strip()
        if not normalized_search:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A valid drawing search is required",
            )
        escaped = (
            normalized_search.lower()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        query = query.filter(
            or_(
                func.lower(DrawingSheet.sheet_number).like(
                    pattern, escape="\\"
                ),
                func.lower(DrawingSheet.title).like(pattern, escape="\\"),
                func.lower(DrawingSet.name).like(pattern, escape="\\"),
                func.lower(DrawingRevision.revision_code).like(
                    pattern, escape="\\"
                ),
            )
        )
    total = query.count()
    sort_columns = {
        "sheet_number": DrawingSheet.sort_key,
        "title": func.lower(DrawingSheet.title),
        "discipline": DrawingSheet.discipline,
        "revision_date": DrawingRevision.revision_date,
        "updated_at": DrawingSheet.updated_at,
    }
    primary = (
        sort_columns[sort].desc()
        if order == "desc"
        else sort_columns[sort].asc()
    )
    sheets = (
        query.order_by(primary, DrawingSheet.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "project_id": project_id,
        "sheets": _sheet_responses(db, sheets),
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(sheets) < total,
        },
    }
