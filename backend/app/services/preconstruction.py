from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from time import perf_counter
import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    PRECONSTRUCTION_EXECUTION_CONFIG,
    PRECONSTRUCTION_PREPARATION_CONFIG,
    PRECONSTRUCTION_SCOPE_CONFIG,
    PreconstructionAIConfig,
    PreconstructionExecutionConfig,
    PreconstructionPreparationConfig,
)
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.drawing import DrawingRevision, DrawingSheet
from app.models.preconstruction import (
    PreconstructionAnalysisAttempt,
    PreconstructionAnalysisRun,
    PreconstructionContentPage,
    PreconstructionPreparationRun,
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)
from app.preconstruction.provider import (
    PreconstructionAIProvider,
    ProviderError,
    ProviderContentSegment,
    ProviderRequest,
    ProviderResult,
    ProviderSourceDescriptor,
)
from app.preconstruction.roles import (
    ANALYSIS_TYPES,
    CONTENT_DEPENDENT_ANALYSIS_TYPES,
    DOCUMENT_ROLES,
    DOCUMENT_ROLE_BY_VALUE,
    REVIEW_PURPOSES,
)
from app.schemas.preconstruction import (
    AnalysisRunCreate,
    ReviewSetCreate,
    ReviewSetUpdate,
    ReviewSourceCreate,
    ReviewSourceUpdate,
)
from app.preconstruction.assertions import ASSERTION_TYPES, INCLUSION_STATES
from app.preconstruction.taxonomy import (
    ACTIVE_CONCEPT_CODES,
    SUPPORTED_TAXONOMY_VERSIONS,
)
from app.preconstruction.execution import ExecutionMetrics
from app.services.preconstruction_content import (
    retrieve_snapshot_segments,
    source_preparation_states,
)
from app.services.preconstruction_execution import record_execution_metrics
from app.services.preconstruction_scope import (
    SCOPE_ANALYSIS_TYPE,
    persist_scope_assertions,
    scope_run_summary,
    validate_scope_result,
)


ACTIVE_RUN_STATUSES = ("pending", "processing")
TERMINAL_RUN_STATUSES = (
    "completed",
    "completed_with_warnings",
    "failed",
    "cancelled",
    "unavailable",
)
SEARCHABLE_EXTRACTION_STATUSES = ("completed", "completed_with_warnings")
MAX_READINESS_MESSAGES = 50


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def get_review_set(
    db: Session,
    project_id: int,
    review_set_id: int,
) -> PreconstructionReviewSet:
    review_set = (
        db.query(PreconstructionReviewSet)
        .filter(
            PreconstructionReviewSet.id == review_set_id,
            PreconstructionReviewSet.project_id == project_id,
        )
        .first()
    )
    if review_set is None:
        raise _not_found("Preconstruction review set not found")
    return review_set


def _require_editable(review_set: PreconstructionReviewSet) -> None:
    if review_set.status == "archived":
        raise _conflict("Archived preconstruction review sets are read-only")
    if review_set.status != "draft":
        raise _conflict("Review set sources are locked after an analysis run")


def review_set_response(review_set: PreconstructionReviewSet) -> dict:
    return {
        "id": review_set.id,
        "project_id": review_set.project_id,
        "name": review_set.name,
        "description": review_set.description,
        "purpose": review_set.purpose,
        "purpose_label": REVIEW_PURPOSES[review_set.purpose],
        "status": review_set.status,
        "created_by": review_set.created_by,
        "created_at": review_set.created_at,
        "updated_at": review_set.updated_at,
        "archived_at": review_set.archived_at,
    }


def create_review_set(
    db: Session,
    project_id: int,
    user_id: int,
    payload: ReviewSetCreate,
) -> PreconstructionReviewSet:
    review_set = PreconstructionReviewSet(
        project_id=project_id,
        name=payload.name,
        normalized_name=_normalized_name(payload.name),
        description=payload.description or None,
        purpose=payload.purpose,
        status="draft",
        created_by=user_id,
    )
    db.add(review_set)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict(
            "A preconstruction review set with this name already exists"
        ) from error
    db.refresh(review_set)
    return review_set


def list_review_sets(
    db: Session,
    project_id: int,
    *,
    state: str,
    limit: int,
    offset: int,
) -> tuple[list[PreconstructionReviewSet], int]:
    query = db.query(PreconstructionReviewSet).filter(
        PreconstructionReviewSet.project_id == project_id
    )
    if state == "active":
        query = query.filter(PreconstructionReviewSet.status != "archived")
    elif state == "archived":
        query = query.filter(PreconstructionReviewSet.status == "archived")
    total = query.count()
    items = (
        query.order_by(
            PreconstructionReviewSet.created_at.desc(),
            PreconstructionReviewSet.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def update_review_set(
    db: Session,
    review_set: PreconstructionReviewSet,
    payload: ReviewSetUpdate,
) -> PreconstructionReviewSet:
    _require_editable(review_set)
    values = payload.model_dump(exclude_unset=True)
    if "name" in values:
        review_set.normalized_name = _normalized_name(values["name"])
    for field, value in values.items():
        setattr(review_set, field, value or None if field == "description" else value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict(
            "A preconstruction review set with this name already exists"
        ) from error
    db.refresh(review_set)
    return review_set


def archive_review_set(
    db: Session,
    review_set: PreconstructionReviewSet,
) -> PreconstructionReviewSet:
    if review_set.status == "archived":
        return review_set
    active = (
        db.query(PreconstructionAnalysisRun.id)
        .filter(
            PreconstructionAnalysisRun.review_set_id == review_set.id,
            PreconstructionAnalysisRun.status.in_(ACTIVE_RUN_STATUSES),
        )
        .first()
    )
    if active:
        raise _conflict("Cancel active analysis runs before archiving this review set")
    active_preparation = (
        db.query(PreconstructionPreparationRun.id)
        .join(
            PreconstructionReviewSource,
            PreconstructionReviewSource.id
            == PreconstructionPreparationRun.review_source_id,
        )
        .filter(
            PreconstructionReviewSource.review_set_id == review_set.id,
            PreconstructionPreparationRun.status.in_(("pending", "processing")),
        )
        .first()
    )
    if active_preparation:
        raise _conflict(
            "Cancel active source preparation before archiving this review set"
        )
    review_set.status = "archived"
    review_set.archived_at = utc_now()
    db.commit()
    db.refresh(review_set)
    return review_set


@dataclass(frozen=True)
class ResolvedSource:
    document: Document
    revision: DrawingRevision | None
    sheet: DrawingSheet | None
    extraction: DocumentExtraction | None
    display_name: str
    sheet_number: str | None
    revision_code: str | None
    route_target: dict


def resolve_source(
    db: Session,
    project_id: int,
    *,
    source_type: str,
    document_id: int,
    drawing_revision_id: int | None,
) -> ResolvedSource:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        )
        .first()
    )
    if document is None:
        raise _not_found("Review source not found")

    revision = None
    sheet = None
    if source_type == "drawing_revision":
        revision = (
            db.query(DrawingRevision)
            .filter(
                DrawingRevision.id == drawing_revision_id,
                DrawingRevision.project_id == project_id,
                DrawingRevision.document_id == document_id,
            )
            .first()
        )
        if revision is None:
            raise _not_found("Review source not found")
        sheet = (
            db.query(DrawingSheet)
            .filter(
                DrawingSheet.id == revision.drawing_sheet_id,
                DrawingSheet.project_id == project_id,
            )
            .first()
        )
        if sheet is None:
            raise _not_found("Review source not found")

    extraction = (
        db.query(DocumentExtraction)
        .filter(
            DocumentExtraction.document_id == document.id,
            DocumentExtraction.project_id == project_id,
        )
        .first()
    )
    if revision and sheet:
        display_name = f"{sheet.sheet_number} - {sheet.title}"
        route_target = {
            "page": "drawingViewer",
            "projectId": project_id,
            "sheetId": sheet.id,
            "revisionId": revision.id,
        }
    else:
        display_name = document.display_name
        route_target = {
            "page": "projectDocuments",
            "projectId": project_id,
            "documentId": document.id,
        }
    return ResolvedSource(
        document=document,
        revision=revision,
        sheet=sheet,
        extraction=extraction,
        display_name=display_name,
        sheet_number=sheet.sheet_number if sheet else None,
        revision_code=revision.revision_code if revision else None,
        route_target=route_target,
    )


def get_review_source(
    db: Session,
    project_id: int,
    review_set_id: int,
    source_id: int,
) -> PreconstructionReviewSource:
    source = (
        db.query(PreconstructionReviewSource)
        .filter(
            PreconstructionReviewSource.id == source_id,
            PreconstructionReviewSource.project_id == project_id,
            PreconstructionReviewSource.review_set_id == review_set_id,
            PreconstructionReviewSource.removed_at.is_(None),
        )
        .first()
    )
    if source is None:
        raise _not_found("Preconstruction review source not found")
    return source


def source_response(
    source: PreconstructionReviewSource,
    preparation_state: dict | None = None,
) -> dict:
    role = DOCUMENT_ROLE_BY_VALUE[source.document_role]
    route_target = (
        {
            "page": "projectDrawings",
            "projectId": source.project_id,
            "revisionId": source.drawing_revision_id,
        }
        if source.source_type == "drawing_revision"
        else {
            "page": "projectDocuments",
            "projectId": source.project_id,
            "documentId": source.document_id,
        }
    )
    preparation = preparation_state or {
        "current_extraction_status": source.extraction_status,
        "preparation_status": "not_prepared",
        "preparation_run_id": None,
        "content_snapshot_id": None,
        "prepared_at": None,
        "page_count": 0,
        "segment_count": 0,
        "total_character_count": 0,
        "preparation_extraction_method": None,
        "warning_count": 0,
        "unavailable_reason": None,
        "lineage_current": False,
        "stale_reason": None,
    }
    return {
        "id": source.id,
        "project_id": source.project_id,
        "review_set_id": source.review_set_id,
        "source_type": source.source_type,
        "document_id": source.document_id,
        "drawing_revision_id": source.drawing_revision_id,
        "document_role": source.document_role,
        "role_label": role.label,
        "role_category": role.category,
        "discipline": source.discipline,
        "trade": source.trade,
        "source_checksum": source.source_checksum,
        "extraction_id": source.extraction_id,
        "extraction_version": source.extraction_version,
        "extraction_status": source.extraction_status,
        "display_name": source.display_name_snapshot,
        "sheet_number": source.sheet_number_snapshot,
        "revision_code": source.revision_code_snapshot,
        "route_target": route_target,
        "added_by": source.added_by,
        "added_at": source.added_at,
        "locked": source.locked_at is not None,
        **{
            key: preparation[key]
            for key in (
                "current_extraction_status",
                "preparation_status",
                "preparation_run_id",
                "content_snapshot_id",
                "prepared_at",
                "page_count",
                "segment_count",
                "total_character_count",
                "preparation_extraction_method",
                "warning_count",
                "unavailable_reason",
                "lineage_current",
                "stale_reason",
            )
        },
    }


def list_review_sources(
    db: Session,
    project_id: int,
    review_set_id: int,
) -> list[PreconstructionReviewSource]:
    return (
        db.query(PreconstructionReviewSource)
        .filter(
            PreconstructionReviewSource.project_id == project_id,
            PreconstructionReviewSource.review_set_id == review_set_id,
            PreconstructionReviewSource.removed_at.is_(None),
        )
        .order_by(PreconstructionReviewSource.added_at.asc(), PreconstructionReviewSource.id.asc())
        .all()
    )


def add_review_source(
    db: Session,
    project_id: int,
    review_set: PreconstructionReviewSet,
    user_id: int,
    payload: ReviewSourceCreate,
    config: PreconstructionAIConfig,
) -> PreconstructionReviewSource:
    _require_editable(review_set)
    count = (
        db.query(func.count(PreconstructionReviewSource.id))
        .filter(
            PreconstructionReviewSource.review_set_id == review_set.id,
            PreconstructionReviewSource.removed_at.is_(None),
        )
        .scalar()
    )
    if count >= config.max_sources_per_review:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Review set source limit reached",
        )
    resolved = resolve_source(
        db,
        project_id,
        source_type=payload.source_type,
        document_id=payload.document_id,
        drawing_revision_id=payload.drawing_revision_id,
    )
    extraction = resolved.extraction
    source = PreconstructionReviewSource(
        project_id=project_id,
        review_set_id=review_set.id,
        source_type=payload.source_type,
        document_id=resolved.document.id,
        drawing_revision_id=resolved.revision.id if resolved.revision else None,
        document_role=payload.document_role,
        discipline=payload.discipline or None,
        trade=payload.trade or None,
        source_checksum=resolved.document.checksum_sha256,
        extraction_id=extraction.id if extraction else None,
        extraction_version=extraction.extractor_version if extraction else None,
        extraction_status=extraction.status if extraction else "not_processed",
        display_name_snapshot=resolved.display_name,
        sheet_number_snapshot=resolved.sheet_number,
        revision_code_snapshot=resolved.revision_code,
        added_by=user_id,
    )
    db.add(source)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise _conflict("This source is already active in the review set") from error
    db.refresh(source)
    return source


def update_review_source(
    db: Session,
    review_set: PreconstructionReviewSet,
    source: PreconstructionReviewSource,
    payload: ReviewSourceUpdate,
) -> PreconstructionReviewSource:
    _require_editable(review_set)
    if source.locked_at is not None:
        raise _conflict("Review sources used by an analysis run are immutable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value or None if field in {"discipline", "trade"} else value)
    db.commit()
    db.refresh(source)
    return source


def remove_review_source(
    db: Session,
    review_set: PreconstructionReviewSet,
    source: PreconstructionReviewSource,
) -> None:
    _require_editable(review_set)
    if source.locked_at is not None:
        raise _conflict("Review sources used by an analysis run are immutable")
    source.removed_at = utc_now()
    db.commit()


def list_source_candidates(
    db: Session,
    project_id: int,
    *,
    source_type: str,
    search: str,
    limit: int,
) -> list[dict]:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    if source_type == "document":
        drawing_document_ids = db.query(DrawingRevision.document_id).filter(
            DrawingRevision.project_id == project_id
        )
        query = db.query(Document).filter(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.is_current_version.is_(True),
            ~Document.id.in_(drawing_document_ids),
        )
        if search:
            query = query.filter(
                or_(
                    Document.display_name.ilike(pattern, escape="\\"),
                    Document.document_type.ilike(pattern, escape="\\"),
                )
            )
        documents = query.order_by(Document.display_name.asc(), Document.id.asc()).limit(limit).all()
        extraction_by_document = {
            item.document_id: item
            for item in db.query(DocumentExtraction).filter(
                DocumentExtraction.document_id.in_([item.id for item in documents])
            )
        } if documents else {}
        return [
            {
                "source_type": "document",
                "document_id": document.id,
                "drawing_revision_id": None,
                "display_name": document.display_name,
                "document_type": document.document_type,
                "extraction_status": (
                    extraction_by_document[document.id].status
                    if document.id in extraction_by_document
                    else "not_processed"
                ),
                "sheet_number": None,
                "revision_code": None,
                "is_current_revision": None,
                "route_target": {
                    "page": "projectDocuments",
                    "projectId": project_id,
                    "documentId": document.id,
                },
            }
            for document in documents
        ]

    query = (
        db.query(DrawingRevision, DrawingSheet, Document, DocumentExtraction)
        .join(DrawingSheet, DrawingSheet.id == DrawingRevision.drawing_sheet_id)
        .join(Document, Document.id == DrawingRevision.document_id)
        .outerjoin(DocumentExtraction, DocumentExtraction.document_id == Document.id)
        .filter(
            DrawingRevision.project_id == project_id,
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        )
    )
    if search:
        query = query.filter(
            or_(
                DrawingSheet.sheet_number.ilike(pattern, escape="\\"),
                DrawingSheet.title.ilike(pattern, escape="\\"),
                DrawingRevision.revision_code.ilike(pattern, escape="\\"),
            )
        )
    rows = query.order_by(
        DrawingSheet.sort_key.asc(), DrawingRevision.sequence_number.desc(), DrawingRevision.id.desc()
    ).limit(limit).all()
    return [
        {
            "source_type": "drawing_revision",
            "document_id": document.id,
            "drawing_revision_id": revision.id,
            "display_name": f"{sheet.sheet_number} - {sheet.title}",
            "document_type": document.document_type,
            "extraction_status": extraction.status if extraction else "not_processed",
            "sheet_number": sheet.sheet_number,
            "revision_code": revision.revision_code,
            "is_current_revision": revision.is_current,
            "route_target": {
                "page": "drawingViewer",
                "projectId": project_id,
                "sheetId": sheet.id,
                "revisionId": revision.id,
            },
        }
        for revision, sheet, document, extraction in rows
    ]


def _current_source_states(
    db: Session,
    sources: list[PreconstructionReviewSource],
) -> dict[int, tuple[Document | None, DocumentExtraction | None]]:
    document_ids = sorted({source.document_id for source in sources})
    if not document_ids:
        return {}
    project_id = sources[0].project_id
    documents = db.query(Document).filter(
        Document.project_id == project_id,
        Document.id.in_(document_ids),
    ).all()
    documents_by_id = {document.id: document for document in documents}
    extractions = db.query(DocumentExtraction).filter(
        DocumentExtraction.project_id == project_id,
        DocumentExtraction.document_id.in_(document_ids),
    ).all()
    extractions_by_document = {
        extraction.document_id: extraction for extraction in extractions
    }
    return {
        source.id: (
            documents_by_id.get(source.document_id),
            extractions_by_document.get(source.document_id),
        )
        for source in sources
    }


def _composition_messages(review_set: PreconstructionReviewSet, sources: list) -> list[str]:
    roles = {source.document_role for source in sources}
    categories = {DOCUMENT_ROLE_BY_VALUE[role].category for role in roles}
    blockers = []
    if review_set.purpose == "revision_impact_review":
        if sum(source.source_type == "drawing_revision" for source in sources) < 2:
            blockers.append("At least two drawing revisions are required for revision impact review.")
        return blockers
    if "requirement" not in categories:
        blockers.append("At least one requirement source is required.")
    purpose_coverage = {
        "bid_scope_review": {"proposal"},
        "subcontract_scope_review": {"proposal", "subcontract"},
        "procurement_review": {"purchase_order", "procurement_package"},
        "submittal_coverage_review": {"submittal"},
        "general_scope_review": {
            "proposal", "subcontract", "purchase_order", "procurement_package", "submittal"
        },
    }[review_set.purpose]
    if not roles.intersection(purpose_coverage):
        label = REVIEW_PURPOSES[review_set.purpose]
        blockers.append(f"A compatible coverage source is required for {label.lower()}.")
    return blockers


def _build_manifest_payload(
    db: Session,
    review_set: PreconstructionReviewSet,
    sources: list[PreconstructionReviewSource],
    config: PreconstructionAIConfig,
    analysis_type: str,
    source_states: dict[
        int,
        tuple[Document | None, DocumentExtraction | None],
    ] | None = None,
    preparation_states: dict[int, dict] | None = None,
) -> dict:
    states = source_states or _current_source_states(db, sources)
    manifest_sources = []
    for source in sorted(sources, key=lambda item: item.id):
        document, extraction = states[source.id]
        source_payload = {
                "source_id": source.id,
                "source_type": source.source_type,
                "document_id": source.document_id,
                "drawing_revision_id": source.drawing_revision_id,
                "document_role": source.document_role,
                "discipline": source.discipline,
                "trade": source.trade,
                "checksum": document.checksum_sha256 if document else source.source_checksum,
                "extraction_id": extraction.id if extraction else None,
                "extraction_version": extraction.extractor_version if extraction else None,
                "extraction_status": extraction.status if extraction else "not_processed",
                "display_name": source.display_name_snapshot,
                "sheet_number": source.sheet_number_snapshot,
                "revision_code": source.revision_code_snapshot,
        }
        if analysis_type in CONTENT_DEPENDENT_ANALYSIS_TYPES:
            preparation = (preparation_states or {})[source.id]
            source_payload["content_snapshot"] = {
                "id": preparation["content_snapshot_id"],
                "lineage_fingerprint": preparation["lineage_fingerprint"],
                "content_hash": preparation["content_hash"],
                "page_count": preparation["page_count"],
                "segment_count": preparation["segment_count"],
                "preparation_version": preparation["preparation_version"],
                "segmentation_policy_version": preparation["segmentation_policy_version"],
                "extraction_method": preparation["snapshot_extraction_method"],
                "extractor_version": preparation["snapshot_extractor_version"],
            }
        manifest_sources.append(source_payload)
    return {
        "analysis_type": analysis_type,
        "provider_profile": config.provider,
        "review_set_id": review_set.id,
        "schema_version": config.schema_version,
        "sources": manifest_sources,
        "template_version": config.template_version,
    }


def canonical_manifest(payload: dict, max_bytes: int) -> tuple[str, str]:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(serialized.encode("utf-8")) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Review manifest exceeds the configured size limit",
        )
    return serialized, sha256(serialized.encode("utf-8")).hexdigest()


def review_readiness(
    db: Session,
    review_set: PreconstructionReviewSet,
    config: PreconstructionAIConfig,
    provider: PreconstructionAIProvider,
    *,
    analysis_type: str = "provider_contract_validation",
    preparation_config: PreconstructionPreparationConfig = PRECONSTRUCTION_PREPARATION_CONFIG,
) -> dict:
    sources = list_review_sources(db, review_set.project_id, review_set.id)
    source_states = _current_source_states(db, sources)
    blockers = []
    warnings = []
    counts = {"requirement": 0, "coverage": 0, "context": 0}
    searchable = 0
    unavailable = 0
    preparation_states = source_preparation_states(db, sources, preparation_config)
    prepared = 0
    preparation_warnings = 0
    preparation_missing = 0
    preparation_stale = 0
    preparation_unavailable = 0
    if not sources:
        blockers.append("At least one review source is required.")
    for source in sources:
        category = DOCUMENT_ROLE_BY_VALUE[source.document_role].category
        counts[category] += 1
        document, extraction = source_states[source.id]
        issue_prefix = source.display_name_snapshot
        if document is None or document.deleted_at is not None:
            blockers.append(f"{issue_prefix} is no longer available.")
            unavailable += 1
            continue
        if document.checksum_sha256 != source.source_checksum:
            blockers.append(f"{issue_prefix} no longer matches its pinned checksum.")
            unavailable += 1
            continue
        extraction_ready = bool(
            extraction
            and extraction.status in SEARCHABLE_EXTRACTION_STATUSES
            and extraction.searchable
            and extraction.source_checksum == document.checksum_sha256
        )
        if extraction_ready:
            searchable += 1
        else:
            unavailable += 1
            message = f"{issue_prefix} is not searchable yet."
            if category == "context":
                warnings.append(message)
            else:
                blockers.append(message)
        preparation = preparation_states[source.id]
        preparation_status = preparation["preparation_status"]
        if preparation_status in ("ready", "ready_with_warnings"):
            prepared += 1
            if preparation_status == "ready_with_warnings":
                preparation_warnings += 1
                warnings.append(f"{issue_prefix} preparation completed with warnings.")
        elif preparation_status == "stale":
            preparation_stale += 1
            message = f"{issue_prefix} prepared content is stale."
            (blockers if analysis_type in CONTENT_DEPENDENT_ANALYSIS_TYPES else warnings).append(message)
        elif preparation_status in ("unavailable", "failed"):
            preparation_unavailable += 1
            message = f"{issue_prefix} content preparation is {preparation_status}."
            (blockers if analysis_type in CONTENT_DEPENDENT_ANALYSIS_TYPES else warnings).append(message)
        else:
            preparation_missing += 1
            message = f"{issue_prefix} content preparation is {preparation_status.replace('_', ' ')}."
            (blockers if analysis_type in CONTENT_DEPENDENT_ANALYSIS_TYPES else warnings).append(message)
    blockers.extend(_composition_messages(review_set, sources))
    if review_set.status == "archived":
        blockers.append("Archived review sets cannot start analysis runs.")
    if not config.enabled or not provider.available:
        blockers.append("AI provider is disabled.")

    prepared_characters = sum(
        preparation_states[source.id]["total_character_count"] for source in sources
    )
    if analysis_type == SCOPE_ANALYSIS_TYPE:
        if (
            PRECONSTRUCTION_SCOPE_CONFIG.taxonomy_version
            not in SUPPORTED_TAXONOMY_VERSIONS
        ):
            blockers.append("The configured scope taxonomy version is unavailable.")
        if prepared_characters > PRECONSTRUCTION_SCOPE_CONFIG.request_max_content_characters:
            blockers.append(
                "Prepared content exceeds the configured scope analysis limit."
            )

    blockers = blockers[:MAX_READINESS_MESSAGES]
    warnings = warnings[:MAX_READINESS_MESSAGES]
    preview_hash = None
    if sources:
        payload = _build_manifest_payload(
            db,
            review_set,
            sources,
            config,
            analysis_type,
            source_states,
            preparation_states,
        )
        _, preview_hash = canonical_manifest(payload, config.max_manifest_bytes)
    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "source_count": len(sources),
        "requirement_source_count": counts["requirement"],
        "coverage_source_count": counts["coverage"],
        "context_source_count": counts["context"],
        "searchable_source_count": searchable,
        "unavailable_source_count": unavailable,
        "prepared_source_count": prepared,
        "preparation_warning_source_count": preparation_warnings,
        "missing_preparation_source_count": preparation_missing,
        "stale_preparation_source_count": preparation_stale,
        "unavailable_preparation_source_count": preparation_unavailable,
        "manifest_preview_hash": preview_hash,
        "analysis_type": analysis_type,
        "prepared_character_count": prepared_characters,
        "scope_taxonomy_version": PRECONSTRUCTION_SCOPE_CONFIG.taxonomy_version,
        "scope_extraction_available": bool(
            config.enabled
            and provider.available
            and PRECONSTRUCTION_SCOPE_CONFIG.taxonomy_version
            in SUPPORTED_TAXONOMY_VERSIONS
        ),
        "provider": {
            "profile": config.provider,
            "available": bool(config.enabled and provider.available),
            "capability": provider.capability_label,
        },
    }


def run_response(run: PreconstructionAnalysisRun) -> dict:
    summary = json.loads(run.result_summary_json) if run.result_summary_json else None
    warnings = summary.get("warnings", []) if summary else []
    return {
        "id": run.id,
        "review_set_id": run.review_set_id,
        "analysis_type": run.analysis_type,
        "analysis_type_label": ANALYSIS_TYPES[run.analysis_type],
        "status": run.status,
        "provider_profile": run.provider_profile,
        "manifest_hash": run.manifest_hash,
        "source_count": run.source_count,
        "requested_at": run.requested_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "failed_at": run.failed_at,
        "cancelled_at": run.cancelled_at,
        "attempt_count": run.current_attempt_count,
        "max_attempts": run.max_attempts,
        "failure_code": run.failure_code,
        "failure_message": run.failure_message,
        "warnings": warnings,
        "result_summary": summary,
        "can_cancel": run.status in ACTIVE_RUN_STATUSES,
        "can_retry": run.status in ("failed", "unavailable") and run.current_attempt_count < run.max_attempts,
    }


def create_analysis_run(
    db: Session,
    review_set: PreconstructionReviewSet,
    user_id: int,
    payload: AnalysisRunCreate,
    config: PreconstructionAIConfig,
    provider: PreconstructionAIProvider,
    preparation_config: PreconstructionPreparationConfig = PRECONSTRUCTION_PREPARATION_CONFIG,
) -> PreconstructionAnalysisRun:
    readiness = review_readiness(
        db,
        review_set,
        config,
        provider,
        analysis_type=payload.analysis_type,
        preparation_config=preparation_config,
    )
    if not readiness["ready"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Review set is not ready", "blockers": readiness["blockers"]},
        )
    sources = list_review_sources(db, review_set.project_id, review_set.id)
    preparation_states = source_preparation_states(db, sources, preparation_config)
    manifest, manifest_hash = canonical_manifest(
        _build_manifest_payload(
            db,
            review_set,
            sources,
            config,
            payload.analysis_type,
            preparation_states=preparation_states,
        ),
        config.max_manifest_bytes,
    )
    run = PreconstructionAnalysisRun(
        project_id=review_set.project_id,
        review_set_id=review_set.id,
        status="pending",
        provider_profile=config.provider,
        analysis_type=payload.analysis_type,
        manifest_hash=manifest_hash,
        manifest_json=manifest,
        source_count=len(sources),
        template_version=config.template_version,
        schema_version=config.schema_version,
        requested_by=user_id,
        current_attempt_count=1,
        max_attempts=config.max_attempts,
    )
    db.add(run)
    try:
        db.flush()
        attempt = PreconstructionAnalysisAttempt(
            project_id=review_set.project_id,
            run_id=run.id,
            attempt_number=1,
            provider_profile=config.provider,
            provider_name=provider.provider_name,
            model_name=provider.model_name,
            status="pending",
            input_manifest_hash=manifest_hash,
            output_schema_version=config.schema_version,
        )
        db.add(attempt)
        now = utc_now()
        for source in sources:
            source.locked_at = now
        review_set.status = "ready"
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = (
            db.query(PreconstructionAnalysisRun)
            .filter(
                PreconstructionAnalysisRun.review_set_id == review_set.id,
                PreconstructionAnalysisRun.manifest_hash == manifest_hash,
                PreconstructionAnalysisRun.provider_profile == config.provider,
                PreconstructionAnalysisRun.analysis_type == payload.analysis_type,
                PreconstructionAnalysisRun.status.in_(ACTIVE_RUN_STATUSES),
            )
            .first()
        )
        if existing:
            return existing
        raise _conflict("An identical analysis run is already active") from error
    db.refresh(run)
    return run


def list_analysis_runs(
    db: Session,
    project_id: int,
    review_set_id: int,
    *,
    limit: int,
    offset: int,
) -> tuple[list[PreconstructionAnalysisRun], int]:
    query = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.project_id == project_id,
        PreconstructionAnalysisRun.review_set_id == review_set_id,
    )
    total = query.count()
    return (
        query.order_by(
            PreconstructionAnalysisRun.requested_at.desc(),
            PreconstructionAnalysisRun.id.desc(),
        ).offset(offset).limit(limit).all(),
        total,
    )


def get_analysis_run(db: Session, project_id: int, run_id: int) -> PreconstructionAnalysisRun:
    run = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.id == run_id,
        PreconstructionAnalysisRun.project_id == project_id,
    ).first()
    if run is None:
        raise _not_found("Preconstruction analysis run not found")
    return run


def cancel_analysis_run(db: Session, run: PreconstructionAnalysisRun) -> PreconstructionAnalysisRun:
    if run.status not in ACTIVE_RUN_STATUSES:
        raise _conflict("Only pending or processing analysis runs can be cancelled")
    now = utc_now()
    run.status = "cancelled"
    run.cancelled_at = now
    attempts = db.query(PreconstructionAnalysisAttempt).filter(
        PreconstructionAnalysisAttempt.run_id == run.id,
        PreconstructionAnalysisAttempt.status.in_(("pending", "processing")),
    ).all()
    for attempt in attempts:
        attempt.status = "cancelled"
        attempt.completed_at = now
        attempt.lease_token = None
        attempt.lease_expires_at = None
    db.commit()
    db.refresh(run)
    return run


def retry_analysis_run(
    db: Session,
    run: PreconstructionAnalysisRun,
    provider: PreconstructionAIProvider,
) -> PreconstructionAnalysisRun:
    if run.status not in ("failed", "unavailable"):
        raise _conflict("Only failed or unavailable analysis runs can be retried")
    if run.current_attempt_count >= run.max_attempts:
        raise _conflict("Analysis run has reached its maximum attempt count")
    number = run.current_attempt_count + 1
    run.current_attempt_count = number
    run.status = "pending"
    run.failure_code = None
    run.failure_message = None
    run.failed_at = None
    run.cancelled_at = None
    db.add(PreconstructionAnalysisAttempt(
        project_id=run.project_id,
        run_id=run.id,
        attempt_number=number,
        provider_profile=run.provider_profile,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        status="pending",
        input_manifest_hash=run.manifest_hash,
        output_schema_version=run.schema_version,
    ))
    db.commit()
    db.refresh(run)
    return run


@dataclass(frozen=True)
class ClaimedAnalysisAttempt:
    attempt_id: int
    lease_token: str


@dataclass
class AnalysisProcessingResult:
    claimed: int = 0
    completed: int = 0
    warnings: int = 0
    retryable: int = 0
    failed: int = 0
    unavailable: int = 0
    cancelled: int = 0
    skipped: int = 0
    # True when the batch stopped claiming new work inside its runtime budget.
    runtime_budget_reached: bool = False


def _retry_delay(config: PreconstructionAIConfig, attempt_number: int) -> int:
    return min(config.retry_base_seconds * (2 ** max(0, attempt_number - 1)), config.retry_max_seconds)


def recover_expired_attempts(db: Session, config: PreconstructionAIConfig) -> int:
    now = utc_now()
    expired = (
        db.query(PreconstructionAnalysisAttempt)
        .filter(
            PreconstructionAnalysisAttempt.status == "processing",
            PreconstructionAnalysisAttempt.lease_expires_at < now,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    recovered = 0
    for attempt in expired:
        run = db.query(PreconstructionAnalysisRun).filter(
            PreconstructionAnalysisRun.id == attempt.run_id
        ).first()
        attempt.status = "failed"
        attempt.failed_at = now
        attempt.failure_code = "lease_expired"
        attempt.failure_message = "Analysis attempt lease expired"
        attempt.lease_token = None
        attempt.lease_expires_at = None
        if run is None or run.status == "cancelled":
            recovered += 1
            continue
        if attempt.attempt_number < run.max_attempts:
            number = attempt.attempt_number + 1
            run.current_attempt_count = number
            run.status = "pending"
            db.add(PreconstructionAnalysisAttempt(
                project_id=run.project_id,
                run_id=run.id,
                attempt_number=number,
                provider_profile=run.provider_profile,
                provider_name=attempt.provider_name,
                model_name=attempt.model_name,
                status="pending",
                available_at=now + timedelta(seconds=_retry_delay(config, number)),
                input_manifest_hash=run.manifest_hash,
                output_schema_version=run.schema_version,
            ))
        else:
            run.status = "failed"
            run.failed_at = now
            run.failure_code = "lease_expired"
            run.failure_message = "Analysis processing lease expired"
        recovered += 1
    if expired:
        db.commit()
    return recovered


def claim_analysis_attempt(
    db: Session,
    *,
    run_id: int | None,
    lease_seconds: int,
) -> ClaimedAnalysisAttempt | None:
    now = utc_now()
    query = db.query(PreconstructionAnalysisAttempt).filter(
        PreconstructionAnalysisAttempt.status == "pending",
        PreconstructionAnalysisAttempt.available_at <= now,
    )
    if run_id is not None:
        query = query.filter(PreconstructionAnalysisAttempt.run_id == run_id)
    attempt = query.order_by(
        PreconstructionAnalysisAttempt.available_at.asc(),
        PreconstructionAnalysisAttempt.id.asc(),
    ).with_for_update(skip_locked=True).first()
    if attempt is None:
        db.rollback()
        return None
    run = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.id == attempt.run_id
    ).first()
    if run is None or run.status == "cancelled":
        attempt.status = "cancelled"
        attempt.completed_at = now
        db.commit()
        return None
    token = uuid.uuid4().hex
    attempt.status = "processing"
    attempt.lease_token = token
    attempt.lease_expires_at = now + timedelta(seconds=lease_seconds)
    attempt.started_at = now
    run.status = "processing"
    run.started_at = run.started_at or now
    db.commit()
    return ClaimedAnalysisAttempt(attempt.id, token)


def _provider_request(db: Session, run: PreconstructionAnalysisRun) -> ProviderRequest:
    manifest = json.loads(run.manifest_json)
    content_segments = []
    total_characters = 0
    content_truncated = False
    is_scope_run = run.analysis_type == SCOPE_ANALYSIS_TYPE
    content_budget = (
        PRECONSTRUCTION_SCOPE_CONFIG.request_max_content_characters
        if is_scope_run
        else PRECONSTRUCTION_PREPARATION_CONFIG.content_max_response_characters
    )
    if run.analysis_type in CONTENT_DEPENDENT_ANALYSIS_TYPES:
        selected = []
        for source in manifest["sources"]:
            snapshot = source["content_snapshot"]
            remaining = content_budget - total_characters
            if remaining <= 0:
                content_truncated = True
                break
            segments = retrieve_snapshot_segments(
                db,
                run.project_id,
                snapshot["id"],
                max_characters=remaining,
            )
            selected.extend((source["source_id"], snapshot["id"], item) for item in segments)
            total_characters += sum(len(item.text) for item in segments)
            if len(segments) < snapshot["segment_count"]:
                content_truncated = True
        page_ids = {item.page_id for _, _, item in selected}
        page_numbers = {
            page.id: page.page_number
            for page in db.query(PreconstructionContentPage).filter(
                PreconstructionContentPage.project_id == run.project_id,
                PreconstructionContentPage.id.in_(page_ids),
            ).all()
        } if page_ids else {}
        content_segments = [
            ProviderContentSegment(
                segment_id=item.id,
                source_id=source_id,
                snapshot_id=snapshot_id,
                page_number=page_numbers[item.page_id],
                segment_index=item.segment_index,
                text_hash=item.text_hash,
                untrusted_text=item.text,
            )
            for source_id, snapshot_id, item in selected
        ]
    return ProviderRequest(
        manifest_hash=run.manifest_hash,
        analysis_type=run.analysis_type,
        provider_profile=run.provider_profile,
        template_version=run.template_version,
        schema_version=run.schema_version,
        sources=tuple(
            ProviderSourceDescriptor(
                source_id=source["source_id"],
                source_type=source["source_type"],
                document_role=source["document_role"],
                checksum=source["checksum"],
                extraction_status=source["extraction_status"],
                content_snapshot_id=(source.get("content_snapshot") or {}).get("id"),
                lineage_fingerprint=(source.get("content_snapshot") or {}).get("lineage_fingerprint"),
                content_hash=(source.get("content_snapshot") or {}).get("content_hash"),
            )
            for source in manifest["sources"]
        ),
        content_segments=tuple(content_segments),
        total_content_characters=total_characters,
        content_truncated=content_truncated,
        # Taxonomy and enumerations are supplied by trusted code. A provider
        # selects from these values and can never introduce its own.
        taxonomy_version=(
            PRECONSTRUCTION_SCOPE_CONFIG.taxonomy_version if is_scope_run else ""
        ),
        scope_schema_version=(
            PRECONSTRUCTION_SCOPE_CONFIG.schema_version if is_scope_run else ""
        ),
        allowed_concept_codes=(
            tuple(sorted(ACTIVE_CONCEPT_CODES)) if is_scope_run else ()
        ),
        allowed_assertion_types=tuple(ASSERTION_TYPES) if is_scope_run else (),
        allowed_inclusion_states=tuple(INCLUSION_STATES) if is_scope_run else (),
        max_assertions=(
            PRECONSTRUCTION_SCOPE_CONFIG.max_assertions_per_run if is_scope_run else 0
        ),
        max_evidence_per_assertion=(
            PRECONSTRUCTION_SCOPE_CONFIG.max_evidence_per_assertion
            if is_scope_run
            else 0
        ),
    )


def _finalize_provider_failure(
    db: Session,
    attempt_id: int,
    lease_token: str,
    error: ProviderError,
    config: PreconstructionAIConfig,
) -> str:
    attempt = db.query(PreconstructionAnalysisAttempt).filter(
        PreconstructionAnalysisAttempt.id == attempt_id,
        PreconstructionAnalysisAttempt.status == "processing",
        PreconstructionAnalysisAttempt.lease_token == lease_token,
    ).with_for_update().first()
    if attempt is None:
        db.rollback()
        return "skipped"
    run = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.id == attempt.run_id
    ).first()
    now = utc_now()
    attempt.status = "failed"
    attempt.failed_at = now
    attempt.failure_code = error.code
    attempt.failure_message = error.safe_message[:300]
    attempt.lease_token = None
    attempt.lease_expires_at = None
    if run.status == "cancelled":
        db.commit()
        return "cancelled"
    if error.retryable and attempt.attempt_number < run.max_attempts:
        number = attempt.attempt_number + 1
        run.status = "pending"
        run.current_attempt_count = number
        db.add(PreconstructionAnalysisAttempt(
            project_id=run.project_id,
            run_id=run.id,
            attempt_number=number,
            provider_profile=run.provider_profile,
            provider_name=attempt.provider_name,
            model_name=attempt.model_name,
            status="pending",
            available_at=now + timedelta(seconds=_retry_delay(config, number)),
            input_manifest_hash=run.manifest_hash,
            output_schema_version=run.schema_version,
        ))
        outcome = "retryable"
    else:
        run.status = "unavailable" if error.code == "provider_disabled" else "failed"
        run.failed_at = now
        run.failure_code = error.code
        run.failure_message = error.safe_message[:300]
        outcome = "unavailable" if run.status == "unavailable" else "failed"
    db.commit()
    return outcome


def process_claimed_attempt(
    db: Session,
    claim: ClaimedAnalysisAttempt,
    provider: PreconstructionAIProvider,
    config: PreconstructionAIConfig,
) -> str:
    attempt = db.query(PreconstructionAnalysisAttempt).filter(
        PreconstructionAnalysisAttempt.id == claim.attempt_id,
        PreconstructionAnalysisAttempt.status == "processing",
        PreconstructionAnalysisAttempt.lease_token == claim.lease_token,
    ).first()
    if attempt is None:
        return "skipped"
    run = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.id == attempt.run_id
    ).first()
    if run is None or run.status == "cancelled" or attempt.input_manifest_hash != run.manifest_hash:
        return _finalize_provider_failure(
            db, claim.attempt_id, claim.lease_token,
            ProviderError("stale_attempt", "Analysis attempt is no longer current"), config
        )
    request = _provider_request(db, run)
    started = utc_now()
    is_scope_run = run.analysis_type == SCOPE_ANALYSIS_TYPE
    validated_scope = None
    try:
        raw_result = provider.execute(request)
        result = raw_result if isinstance(raw_result, ProviderResult) else ProviderResult.model_validate(raw_result)
        if result.schema_version != run.schema_version:
            raise ProviderError("invalid_provider_result", "AI provider returned an invalid result")
        if is_scope_run:
            # Structured extraction: validate strictly, then store only a
            # compact summary. The raw assertion payload is never persisted
            # into run/attempt history.
            validated_scope = validate_scope_result(
                run, request, result.payload, PRECONSTRUCTION_SCOPE_CONFIG
            )
            safe_summary = scope_run_summary(validated_scope)
            result_limit = PRECONSTRUCTION_SCOPE_CONFIG.max_result_bytes
        else:
            safe_summary = {
                "status": result.status,
                "schema_version": result.schema_version,
                "payload": result.payload,
                "warnings": result.warnings,
            }
            result_limit = config.max_result_bytes
        serialized = json.dumps(safe_summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(serialized.encode("utf-8")) > result_limit:
            raise ProviderError("result_too_large", "AI provider result exceeded configured limits")
    except ValidationError:
        return _finalize_provider_failure(
            db, claim.attempt_id, claim.lease_token,
            ProviderError("invalid_provider_result", "AI provider returned an invalid result"), config
        )
    except ProviderError as error:
        return _finalize_provider_failure(db, claim.attempt_id, claim.lease_token, error, config)
    except Exception:
        return _finalize_provider_failure(
            db, claim.attempt_id, claim.lease_token,
            ProviderError("provider_failure", "AI provider execution failed", retryable=True), config
        )

    attempt = db.query(PreconstructionAnalysisAttempt).filter(
        PreconstructionAnalysisAttempt.id == claim.attempt_id,
        PreconstructionAnalysisAttempt.status == "processing",
        PreconstructionAnalysisAttempt.lease_token == claim.lease_token,
    ).with_for_update().first()
    if attempt is None:
        db.rollback()
        return "skipped"
    run = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.id == attempt.run_id
    ).first()
    if run.status == "cancelled":
        attempt.status = "cancelled"
        attempt.lease_token = None
        attempt.lease_expires_at = None
        db.commit()
        return "cancelled"
    now = utc_now()
    final_status = result.status
    if validated_scope is not None:
        # Persist the assertion set inside this same transaction so the set,
        # the attempt, and the run all commit together. Any failure here
        # propagates and leaves no partial assertion set behind.
        try:
            assertion_set = persist_scope_assertions(
                db, run, validated_scope, PRECONSTRUCTION_SCOPE_CONFIG
            )
        except (ProviderError, SQLAlchemyError) as error:
            db.rollback()
            return _finalize_provider_failure(
                db,
                claim.attempt_id,
                claim.lease_token,
                error
                if isinstance(error, ProviderError)
                else ProviderError(
                    "scope_persistence_failed",
                    "Scope assertions could not be persisted",
                    retryable=True,
                ),
                config,
            )
        serialized = json.dumps(
            scope_run_summary(validated_scope, assertion_set.id),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        final_status = (
            "completed_with_warnings" if validated_scope.warnings else "completed"
        )
    attempt.status = "completed"
    attempt.completed_at = now
    attempt.lease_token = None
    attempt.lease_expires_at = None
    attempt.safe_result_json = serialized
    attempt.provider_request_id = result.provider_request_id
    attempt.input_units = result.input_units
    attempt.output_units = result.output_units
    attempt.latency_ms = max(0, int((now - started).total_seconds() * 1000))
    run.status = final_status
    run.completed_at = now
    run.result_summary_json = serialized
    db.commit()
    return "warnings" if final_status == "completed_with_warnings" else "completed"


def process_analysis_attempts(
    db: Session,
    provider: PreconstructionAIProvider,
    config: PreconstructionAIConfig,
    *,
    batch_size: int | None = None,
    max_jobs: int | None = None,
    run_id: int | None = None,
    lease_seconds: int | None = None,
    execution_config: PreconstructionExecutionConfig | None = None,
) -> AnalysisProcessingResult:
    """Claim and process a finite batch, stopping inside the runtime budget.

    The budget stops the loop claiming *new* work; an attempt already claimed
    always finishes. Keeping the budget inside one lease window means this
    process can never still be working on an attempt whose lease has expired
    and been recovered elsewhere.
    """
    execution_config = execution_config or PRECONSTRUCTION_EXECUTION_CONFIG
    result = AnalysisProcessingResult()
    recover_expired_attempts(db, config)
    target = min(batch_size or config.batch_size, config.batch_size)
    if max_jobs is not None:
        target = min(target, max_jobs)
    deadline = perf_counter() + execution_config.worker_max_runtime_seconds
    for _ in range(target):
        if perf_counter() >= deadline:
            result.runtime_budget_reached = True
            break
        claim = claim_analysis_attempt(
            db, run_id=run_id, lease_seconds=lease_seconds or config.lease_seconds
        )
        if claim is None:
            break
        result.claimed += 1
        started = perf_counter()
        outcome = process_claimed_attempt(db, claim, provider, config)
        setattr(result, outcome, getattr(result, outcome) + 1)
        _record_attempt_metrics(
            db, claim, started, execution_config, result.runtime_budget_reached
        )
    return result


def _record_attempt_metrics(
    db: Session,
    claim,
    started: float,
    execution_config: PreconstructionExecutionConfig,
    budget_reached: bool,
) -> None:
    """Append one metric row for a processed attempt. Never fails the batch."""
    attempt = (
        db.query(PreconstructionAnalysisAttempt)
        .filter(PreconstructionAnalysisAttempt.id == claim.attempt_id)
        .first()
    )
    if attempt is None:
        return
    try:
        record_execution_metrics(
            db,
            attempt.project_id,
            ExecutionMetrics(
                execution_kind="analysis_attempt",
                execution_id=attempt.id,
                phase_durations={
                    "provider": int(max(0.0, perf_counter() - started) * 1000)
                },
                duration_ms=attempt.latency_ms
                or int(max(0.0, perf_counter() - started) * 1000),
                input_units=attempt.input_units,
                output_units=attempt.output_units,
                budget_stop_reason=(
                    "runtime_budget_exceeded" if budget_reached else None
                ),
            ),
            execution_config,
            commit=True,
        )
    except SQLAlchemyError:
        db.rollback()


def retry_failed_runs(
    db: Session,
    provider: PreconstructionAIProvider,
    *,
    run_id: int | None,
    limit: int,
) -> int:
    query = db.query(PreconstructionAnalysisRun).filter(
        PreconstructionAnalysisRun.status.in_(("failed", "unavailable")),
        PreconstructionAnalysisRun.current_attempt_count < PreconstructionAnalysisRun.max_attempts,
    )
    if run_id is not None:
        query = query.filter(PreconstructionAnalysisRun.id == run_id)
    runs = query.order_by(PreconstructionAnalysisRun.id.asc()).limit(limit).all()
    for run in runs:
        retry_analysis_run(db, run, provider)
    return len(runs)
