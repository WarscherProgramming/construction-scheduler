from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.document import Document
from app.models.drawing import (
    DrawingIssue,
    DrawingRevision,
    DrawingSet,
    DrawingSheet,
)
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.services.relationship_rules import ENTITY_TYPES


MAX_IDENTIFIER_LENGTH = 200
MAX_TITLE_LENGTH = 500


@dataclass(frozen=True)
class ResolvedRelationshipEntity:
    type: str
    id: int
    identifier: str
    title: str
    status: str | None
    route: dict | None
    available: bool
    selectable: bool

    def response(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "identifier": self.identifier,
            "title": self.title,
            "status": self.status,
            "route": self.route,
            "available": self.available,
        }


@dataclass(frozen=True)
class EntityResolver:
    model: type
    route_page: str
    identifier: Callable[[Any], str]
    title: Callable[[Any], str]
    status: Callable[[Any], str | None]
    available: Callable[[Any], bool]
    selectable: Callable[[Any], bool]
    search_columns: tuple
    order_by: tuple
    candidate_filters: tuple = ()


def _text(value: object, fallback: str, limit: int) -> str:
    normalized = " ".join(str(value or "").split())
    return (normalized or fallback)[:limit]


def _status(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).replace("_", " ").strip()
    return normalized.title() if normalized.islower() else normalized


ENTITY_LABELS = {
    "document": "Document",
    "drawing_set": "Drawing Set",
    "drawing_sheet": "Drawing Sheet",
    "drawing_revision": "Drawing Revision",
    "drawing_issue": "Drawing Issue",
    "rfi": "RFI",
    "submittal": "Submittal",
    "punch_item": "Punch Item",
    "change_order": "Change Order",
    "daily_log": "Daily Log",
}


ENTITY_RESOLVERS = {
    "document": EntityResolver(
        model=Document,
        route_page="projectDocuments",
        identifier=lambda item: item.display_name,
        title=lambda item: item.original_filename,
        status=lambda item: item.status,
        available=lambda item: item.deleted_at is None,
        selectable=lambda item: (
            item.deleted_at is None and item.is_current_version
        ),
        search_columns=(Document.display_name, Document.original_filename),
        order_by=(func.lower(Document.display_name), Document.id),
        candidate_filters=(
            Document.deleted_at.is_(None),
            Document.is_current_version.is_(True),
        ),
    ),
    "drawing_set": EntityResolver(
        model=DrawingSet,
        route_page="projectDrawings",
        identifier=lambda item: item.name,
        title=lambda item: item.description or "Drawing set",
        status=lambda item: _status(item.status),
        available=lambda item: True,
        selectable=lambda item: (
            item.deleted_at is None and item.status != "archived"
        ),
        search_columns=(DrawingSet.name, DrawingSet.description),
        order_by=(func.lower(DrawingSet.name), DrawingSet.id),
        candidate_filters=(
            DrawingSet.deleted_at.is_(None),
            DrawingSet.status != "archived",
        ),
    ),
    "drawing_sheet": EntityResolver(
        model=DrawingSheet,
        route_page="projectDrawings",
        identifier=lambda item: item.sheet_number,
        title=lambda item: item.title,
        status=lambda item: _status(item.status),
        available=lambda item: True,
        selectable=lambda item: (
            item.deleted_at is None and item.status == "active"
        ),
        search_columns=(DrawingSheet.sheet_number, DrawingSheet.title),
        order_by=(DrawingSheet.sort_key, DrawingSheet.id),
        candidate_filters=(
            DrawingSheet.deleted_at.is_(None),
            DrawingSheet.status == "active",
        ),
    ),
    "drawing_revision": EntityResolver(
        model=DrawingRevision,
        route_page="drawingViewer",
        identifier=lambda item: f"Revision {item.revision_code}",
        title=lambda item: item.description or "Drawing revision",
        status=lambda item: "Current" if item.is_current else "Superseded",
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(
            DrawingRevision.revision_code,
            DrawingRevision.description,
        ),
        order_by=(DrawingRevision.drawing_sheet_id, DrawingRevision.id),
    ),
    "drawing_issue": EntityResolver(
        model=DrawingIssue,
        route_page="projectDrawings",
        identifier=lambda item: item.issue_number,
        title=lambda item: item.name,
        status=lambda item: _status(item.status),
        available=lambda item: item.deleted_at is None,
        selectable=lambda item: (
            item.deleted_at is None and item.status != "void"
        ),
        search_columns=(DrawingIssue.issue_number, DrawingIssue.name),
        order_by=(DrawingIssue.issue_date.desc(), DrawingIssue.id.desc()),
        candidate_filters=(
            DrawingIssue.deleted_at.is_(None),
            DrawingIssue.status != "void",
        ),
    ),
    "rfi": EntityResolver(
        model=RFI,
        route_page="rfis",
        identifier=lambda item: item.number,
        title=lambda item: item.subject,
        status=lambda item: item.status,
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(RFI.number, RFI.subject),
        order_by=(RFI.number, RFI.id),
    ),
    "submittal": EntityResolver(
        model=Submittal,
        route_page="submittals",
        identifier=lambda item: item.number,
        title=lambda item: item.title,
        status=lambda item: item.status,
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(Submittal.number, Submittal.title),
        order_by=(Submittal.number, Submittal.id),
    ),
    "punch_item": EntityResolver(
        model=PunchItem,
        route_page="punchItems",
        identifier=lambda item: item.number,
        title=lambda item: (
            f"{item.location}: {item.description}"
            if item.location
            else item.description
        ),
        status=lambda item: item.status,
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(
            PunchItem.number,
            PunchItem.location,
            PunchItem.description,
        ),
        order_by=(PunchItem.number, PunchItem.id),
    ),
    "change_order": EntityResolver(
        model=ChangeOrder,
        route_page="changeOrders",
        identifier=lambda item: item.co_number,
        title=lambda item: item.title or item.description or "Change order",
        status=lambda item: item.status,
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(
            ChangeOrder.co_number,
            ChangeOrder.title,
            ChangeOrder.description,
        ),
        order_by=(ChangeOrder.co_number, ChangeOrder.id),
    ),
    "daily_log": EntityResolver(
        model=DailyLog,
        route_page="dailyLogs",
        identifier=lambda item: item.date,
        title=lambda item: (
            item.company or item.work_performed or "Daily log"
        ),
        status=lambda item: None,
        available=lambda item: True,
        selectable=lambda item: True,
        search_columns=(DailyLog.date, DailyLog.company),
        order_by=(DailyLog.date.desc(), DailyLog.id.desc()),
    ),
}


def get_entity_resolver(entity_type: str) -> EntityResolver:
    resolver = ENTITY_RESOLVERS.get(entity_type)
    if resolver is None:
        allowed = ", ".join(ENTITY_TYPES)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"entity_type must be one of: {allowed}",
        )
    return resolver


def _revision_sheets(
    db: Session,
    project_id: int,
    revisions: list[DrawingRevision],
) -> dict[int, DrawingSheet]:
    sheet_ids = {item.drawing_sheet_id for item in revisions}
    if not sheet_ids:
        return {}
    return {
        sheet.id: sheet
        for sheet in db.query(DrawingSheet)
        .filter(
            DrawingSheet.project_id == project_id,
            DrawingSheet.id.in_(sheet_ids),
        )
        .all()
    }


def _summary(
    entity_type: str,
    item,
    revision_sheets: dict[int, DrawingSheet],
) -> ResolvedRelationshipEntity:
    resolver = get_entity_resolver(entity_type)
    identifier = resolver.identifier(item)
    title = resolver.title(item)
    route = {"page": resolver.route_page}

    if entity_type == "drawing_revision":
        sheet = revision_sheets.get(item.drawing_sheet_id)
        if sheet is not None:
            identifier = f"{sheet.sheet_number} - Rev {item.revision_code}"
            title = sheet.title
        route.update(
            {
                "sheet_id": item.drawing_sheet_id,
                "revision_id": item.id,
            }
        )

    available = resolver.available(item)
    if not available:
        route = None

    return ResolvedRelationshipEntity(
        type=entity_type,
        id=item.id,
        identifier=_text(
            identifier,
            ENTITY_LABELS[entity_type],
            MAX_IDENTIFIER_LENGTH,
        ),
        title=_text(title, ENTITY_LABELS[entity_type], MAX_TITLE_LENGTH),
        status=_status(resolver.status(item)),
        route=route,
        available=available,
        selectable=resolver.selectable(item),
    )


def unavailable_entity(
    entity_type: str,
    entity_id: int,
) -> ResolvedRelationshipEntity:
    get_entity_resolver(entity_type)
    return ResolvedRelationshipEntity(
        type=entity_type,
        id=entity_id,
        identifier="Related record unavailable",
        title=ENTITY_LABELS[entity_type],
        status="Unavailable",
        route=None,
        available=False,
        selectable=False,
    )


def resolve_entity_summaries(
    db: Session,
    project_id: int,
    references: set[tuple[str, int]],
) -> dict[tuple[str, int], ResolvedRelationshipEntity]:
    grouped: dict[str, set[int]] = {}
    for entity_type, entity_id in references:
        get_entity_resolver(entity_type)
        grouped.setdefault(entity_type, set()).add(entity_id)

    resolved: dict[tuple[str, int], ResolvedRelationshipEntity] = {}
    for entity_type, entity_ids in grouped.items():
        resolver = get_entity_resolver(entity_type)
        items = (
            db.query(resolver.model)
            .filter(
                resolver.model.project_id == project_id,
                resolver.model.id.in_(entity_ids),
            )
            .all()
        )
        revision_sheets = (
            _revision_sheets(db, project_id, items)
            if entity_type == "drawing_revision"
            else {}
        )
        for item in items:
            resolved[(entity_type, item.id)] = _summary(
                entity_type,
                item,
                revision_sheets,
            )

    for reference in references:
        resolved.setdefault(reference, unavailable_entity(*reference))
    return resolved


def resolve_relationship_entity(
    db: Session,
    project_id: int,
    entity_type: str,
    entity_id: int,
    *,
    require_selectable: bool = False,
) -> ResolvedRelationshipEntity:
    summary = resolve_entity_summaries(
        db,
        project_id,
        {(entity_type, entity_id)},
    )[(entity_type, entity_id)]
    if summary.status == "Unavailable":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship entity not found",
        )
    if require_selectable and not summary.selectable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relationship entity is unavailable",
        )
    return summary


def _escaped_search(search: str | None) -> str | None:
    normalized = " ".join(str(search or "").split()).lower()
    if not normalized:
        return None
    escaped = (
        normalized.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def _candidate_query(
    db: Session,
    project_id: int,
    entity_type: str,
) -> Query:
    resolver = get_entity_resolver(entity_type)
    query = db.query(resolver.model).filter(
        resolver.model.project_id == project_id,
        *resolver.candidate_filters,
    )
    if entity_type == "drawing_revision":
        query = (
            query.join(
                DrawingSheet,
                DrawingSheet.id == DrawingRevision.drawing_sheet_id,
            )
            .join(
                DrawingSet,
                DrawingSet.id == DrawingSheet.drawing_set_id,
            )
            .join(Document, Document.id == DrawingRevision.document_id)
            .filter(
                DrawingSheet.deleted_at.is_(None),
                DrawingSheet.status == "active",
                DrawingSet.deleted_at.is_(None),
                DrawingSet.status != "archived",
                Document.deleted_at.is_(None),
            )
        )
    return query


def search_relationship_candidates(
    db: Session,
    project_id: int,
    entity_type: str,
    *,
    search: str | None,
    limit: int,
    exclude_id: int | None,
) -> tuple[list[ResolvedRelationshipEntity], bool]:
    resolver = get_entity_resolver(entity_type)
    query = _candidate_query(db, project_id, entity_type)
    pattern = _escaped_search(search)
    if pattern:
        search_columns = list(resolver.search_columns)
        if entity_type == "drawing_revision":
            search_columns.extend(
                [DrawingSheet.sheet_number, DrawingSheet.title]
            )
        query = query.filter(
            or_(
                *(
                    func.lower(column).like(pattern, escape="\\")
                    for column in search_columns
                )
            )
        )
    if exclude_id is not None:
        query = query.filter(resolver.model.id != exclude_id)

    if entity_type == "drawing_revision":
        query = query.order_by(
            DrawingSheet.sort_key,
            DrawingRevision.sequence_number.desc(),
            DrawingRevision.id.desc(),
        )
    else:
        query = query.order_by(*resolver.order_by)

    items = query.limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]
    summaries = resolve_entity_summaries(
        db,
        project_id,
        {(entity_type, item.id) for item in items},
    )
    return [summaries[(entity_type, item.id)] for item in items], has_more
