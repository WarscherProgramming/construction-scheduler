from datetime import datetime, timezone
import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import Float, and_, case, cast, func, literal, or_
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_extraction import (
    DocumentExtraction,
    DocumentPageText,
)
from app.models.drawing import (
    DrawingRevision,
    DrawingSet,
    DrawingSheet,
)
from app.models.folder import Folder


MAX_QUERY_LENGTH = 200
MAX_SNIPPET_LENGTH = 320
MAX_MATCH_TERMS = 12
SEARCH_CONFIG = "simple"
_TERM_PATTERN = re.compile(r"[\w][\w.-]*", re.UNICODE)


def normalize_search_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    if (
        not normalized
        or len(normalized) > MAX_QUERY_LENGTH
        or any(
            character == "\x00"
            or unicodedata.category(character).startswith("C")
            for character in normalized
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid search query is required",
        )
    return normalized


def _query_terms(query: str) -> tuple[str, ...]:
    terms = []
    for match in _TERM_PATTERN.finditer(query):
        term = match.group(0)
        if term.casefold() not in {value.casefold() for value in terms}:
            terms.append(term)
        if len(terms) >= MAX_MATCH_TERMS:
            break
    return tuple(terms or [query])


def _normalize_snippet_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    plain = "".join(
        " " if character.isspace() else character
        for character in normalized
        if character != "\x00"
        and (
            character.isspace()
            or not unicodedata.category(character).startswith("C")
        )
    )
    return " ".join(plain.split())


def build_search_snippet(
    text: str,
    query: str,
    *,
    maximum: int = MAX_SNIPPET_LENGTH,
) -> tuple[str, list[dict[str, int]]]:
    clean = _normalize_snippet_text(text)
    terms = sorted(_query_terms(query), key=len, reverse=True)
    matches = []
    for term in terms:
        matches.extend(
            (match.start(), match.end())
            for match in re.finditer(
                re.escape(term),
                clean,
                flags=re.IGNORECASE,
            )
        )
    matches.sort()
    first_start = matches[0][0] if matches else 0
    start = max(0, first_start - maximum // 3)
    end = min(len(clean), start + maximum)
    if end - start < maximum:
        start = max(0, end - maximum)
    snippet = clean[start:end]
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    snippet = f"{prefix}{snippet}{suffix}"
    shift = len(prefix) - start

    ranges: list[dict[str, int]] = []
    for match_start, match_end in matches:
        if match_end <= start or match_start >= end:
            continue
        bounded_start = max(match_start, start) + shift
        bounded_end = min(match_end, end) + shift
        if ranges and bounded_start <= ranges[-1]["end"]:
            ranges[-1]["end"] = max(ranges[-1]["end"], bounded_end)
        else:
            ranges.append({"start": bounded_start, "end": bounded_end})
    return snippet, ranges


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _metadata_text(row) -> str:
    return " | ".join(
        value
        for value in (
            row.display_name,
            row.document_type,
            row.sheet_number,
            row.sheet_title,
            row.discipline,
            row.revision_code,
        )
        if value
    )


def _fallback_rank(row, query: str, terms: tuple[str, ...]) -> float:
    normalized_query = query.casefold()
    display_name = row.display_name.casefold()
    sheet_number = (row.sheet_number or "").casefold()
    sheet_title = (row.sheet_title or "").casefold()
    metadata = _metadata_text(row).casefold()
    content = (row.page_text or "").casefold()
    rank = 0.0
    if display_name == normalized_query or sheet_number == normalized_query:
        rank += 12.0
    elif display_name.startswith(normalized_query) or sheet_number.startswith(
        normalized_query
    ):
        rank += 8.0
    if normalized_query in sheet_title:
        rank += 5.0
    if all(term.casefold() in metadata for term in terms):
        rank += 3.0
    if all(term.casefold() in content for term in terms):
        rank += 1.0 + sum(
            content.count(term.casefold()) for term in terms
        ) / 100
    return rank


def _result_from_row(row, query: str, rank: float) -> dict:
    is_drawing = row.drawing_revision_id is not None
    content_matched = bool(row.content_matched)
    source = (
        row.page_text
        if content_matched and row.page_text
        else _metadata_text(row)
    )
    snippet, match_ranges = build_search_snippet(source, query)
    result_type = "drawing_revision" if is_drawing else "document"
    extraction_method = "metadata_only"
    if content_matched:
        extraction_method = (
            row.page_method
            or (
                row.extraction_method
                if row.extraction_method
                in {"embedded_text", "ocr", "mixed"}
                else "metadata_only"
            )
        )
    return {
        "result_type": result_type,
        "document_id": row.document_id,
        "drawing_revision_id": row.drawing_revision_id,
        "drawing_sheet_id": row.drawing_sheet_id,
        "drawing_set_id": row.drawing_set_id,
        "display_name": row.display_name,
        "document_type": row.document_type,
        "sheet_number": row.sheet_number,
        "sheet_title": row.sheet_title,
        "discipline": row.discipline,
        "revision_code": row.revision_code,
        "revision_status": (
            "current" if row.revision_is_current else "superseded"
        )
        if is_drawing
        else None,
        "page_number": row.page_number if content_matched else None,
        "snippet": snippet,
        "match_ranges": match_ranges,
        "rank": max(0.0, round(float(rank), 6)),
        "extraction_method": extraction_method,
        "updated_at": row.updated_at,
        "route_target": {
            "type": result_type,
            "document_id": row.document_id,
            "drawing_sheet_id": row.drawing_sheet_id,
            "drawing_revision_id": row.drawing_revision_id,
        },
    }


def _search_columns(rank_expression, content_match):
    return (
        Document.id.label("document_id"),
        Document.display_name.label("display_name"),
        Document.document_type.label("document_type"),
        Document.updated_at.label("updated_at"),
        DocumentExtraction.extraction_method.label("extraction_method"),
        DocumentPageText.page_number.label("page_number"),
        DocumentPageText.text.label("page_text"),
        DocumentPageText.extraction_method.label("page_method"),
        DrawingRevision.id.label("drawing_revision_id"),
        DrawingRevision.is_current.label("revision_is_current"),
        DrawingRevision.revision_code.label("revision_code"),
        DrawingSheet.id.label("drawing_sheet_id"),
        DrawingSheet.sheet_number.label("sheet_number"),
        DrawingSheet.title.label("sheet_title"),
        DrawingSheet.discipline.label("discipline"),
        DrawingSet.id.label("drawing_set_id"),
        content_match.label("content_matched"),
        rank_expression.label("search_rank"),
    )


def search_project_documents(
    db: Session,
    project_id: int,
    *,
    q: str,
    scope: str,
    document_type: str | None,
    drawing_set_id: int | None,
    discipline: str | None,
    current_revisions_only: bool,
    extraction_method: str | None,
    limit: int,
    offset: int,
) -> dict:
    query_text = normalize_search_query(q)
    terms = _query_terms(query_text)
    dialect = db.get_bind().dialect.name

    page_join = and_(
        DocumentPageText.extraction_id == DocumentExtraction.id,
        DocumentExtraction.searchable.is_(True),
        DocumentExtraction.source_checksum == Document.checksum_sha256,
    )
    base_filters = [
        Document.project_id == project_id,
        Document.deleted_at.is_(None),
        Document.is_current_version.is_(True),
        or_(Document.folder_id.is_(None), Folder.deleted_at.is_(None)),
        or_(
            DrawingRevision.id.is_(None),
            and_(
                DrawingSheet.deleted_at.is_(None),
                DrawingSet.deleted_at.is_(None),
                DrawingSheet.status == "active",
                DrawingSet.status != "archived",
            ),
        ),
    ]
    if scope == "documents":
        base_filters.append(DrawingRevision.id.is_(None))
    elif scope == "drawings":
        base_filters.append(DrawingRevision.id.is_not(None))
    if document_type:
        base_filters.append(
            func.lower(Document.document_type) == document_type.lower()
        )
    if drawing_set_id is not None:
        base_filters.append(DrawingSet.id == drawing_set_id)
    if discipline:
        base_filters.append(
            func.lower(DrawingSheet.discipline) == discipline.lower()
        )
    if current_revisions_only:
        base_filters.append(
            or_(
                DrawingRevision.id.is_(None),
                DrawingRevision.is_current.is_(True),
            )
        )
    if extraction_method:
        base_filters.append(
            func.coalesce(
                DocumentExtraction.extraction_method,
                "metadata_only",
            )
            == extraction_method
        )

    metadata_values = (
        Document.display_name,
        Document.original_filename,
        Document.document_type,
        DrawingSheet.sheet_number,
        DrawingSheet.title,
        DrawingSheet.discipline,
        DrawingRevision.revision_code,
    )
    escaped_query = _escape_like(query_text.casefold())
    exact_pattern = query_text.casefold()
    prefix_pattern = f"{escaped_query}%"

    if dialect == "postgresql":
        tsquery = func.websearch_to_tsquery(SEARCH_CONFIG, query_text)
        metadata_vector = func.to_tsvector(
            SEARCH_CONFIG,
            func.concat_ws(
                " ",
                *(func.coalesce(value, "") for value in metadata_values),
            ),
        )
        metadata_match = metadata_vector.op("@@")(tsquery)
        content_match = DocumentPageText.search_vector.op("@@")(tsquery)
        exact_boost = case(
            (
                or_(
                    func.lower(Document.display_name) == exact_pattern,
                    func.lower(DrawingSheet.sheet_number) == exact_pattern,
                ),
                12.0,
            ),
            else_=0.0,
        )
        prefix_boost = case(
            (
                or_(
                    func.lower(Document.display_name).like(
                        prefix_pattern,
                        escape="\\",
                    ),
                    func.lower(DrawingSheet.sheet_number).like(
                        prefix_pattern,
                        escape="\\",
                    ),
                ),
                8.0,
            ),
            else_=0.0,
        )
        rank_expression = cast(
            exact_boost
            + prefix_boost
            + func.ts_rank_cd(metadata_vector, tsquery) * 4.0
            + func.coalesce(
                func.ts_rank_cd(DocumentPageText.search_vector, tsquery),
                0.0,
            ),
            Float,
        )
        match_filter = or_(
            content_match,
            and_(
                metadata_match,
                or_(
                    DocumentPageText.id.is_(None),
                    DocumentPageText.page_number == 1,
                ),
            ),
        )
    else:
        metadata_term_filters = []
        content_term_filters = []
        for term in terms:
            pattern = f"%{_escape_like(term.casefold())}%"
            metadata_term_filters.append(
                or_(
                    *(
                        func.lower(value).like(pattern, escape="\\")
                        for value in metadata_values
                    )
                )
            )
            content_term_filters.append(
                func.lower(DocumentPageText.normalized_text).like(
                    pattern,
                    escape="\\",
                )
            )
        metadata_match = and_(*metadata_term_filters)
        content_match = and_(*content_term_filters)
        match_filter = or_(
            content_match,
            and_(
                metadata_match,
                or_(
                    DocumentPageText.id.is_(None),
                    DocumentPageText.page_number == 1,
                ),
            ),
        )
        rank_expression = literal(0.0)

    query = (
        db.query(*_search_columns(rank_expression, content_match))
        .outerjoin(Folder, Folder.id == Document.folder_id)
        .outerjoin(
            DocumentExtraction,
            DocumentExtraction.document_id == Document.id,
        )
        .outerjoin(DocumentPageText, page_join)
        .outerjoin(
            DrawingRevision,
            DrawingRevision.document_id == Document.id,
        )
        .outerjoin(
            DrawingSheet,
            DrawingSheet.id == DrawingRevision.drawing_sheet_id,
        )
        .outerjoin(
            DrawingSet,
            DrawingSet.id == DrawingSheet.drawing_set_id,
        )
        .filter(*base_filters, match_filter)
    )

    if dialect == "postgresql":
        total = query.count()
        rows = (
            query.order_by(
                rank_expression.desc(),
                Document.updated_at.desc(),
                Document.id.asc(),
                DocumentPageText.page_number.asc().nullsfirst(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        ranked_rows = [(row, float(row.search_rank or 0)) for row in rows]
    else:
        rows = query.all()
        ranked_rows = [
            (row, _fallback_rank(row, query_text, terms)) for row in rows
        ]
        ranked_rows.sort(
            key=lambda item: (
                -item[1],
                -_datetime_timestamp(item[0].updated_at),
                item[0].document_id,
                item[0].page_number or 0,
            )
        )
        total = len(ranked_rows)
        ranked_rows = ranked_rows[offset : offset + limit]

    results = [
        _result_from_row(row, query_text, rank)
        for row, rank in ranked_rows
    ]
    return {
        "project_id": project_id,
        "query": query_text,
        "scope": scope,
        "results": results,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(results) < total,
        },
    }


def _datetime_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.timestamp()
