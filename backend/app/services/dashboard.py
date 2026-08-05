from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.project import Project
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.models.task import Task
from app.services.schedule_health import get_schedule_health


RFI_OPEN_STATUSES = ("Open", "Pending")
SUBMITTAL_PENDING_STATUSES = ("Draft", "Submitted", "Under Review")
PUNCH_OPEN_STATUSES = ("Open", "In Progress")
PUNCH_COMPLETED_STATUSES = ("Completed", "Verified")
CHANGE_ORDER_ACTIVE_STATUSES = (
    "Draft",
    "Pending",
    "Submitted",
    "Under Review",
)
CHANGE_ORDER_APPROVED_STATUSES = ("Approved", "Executed")
CHANGE_ORDER_REJECTED_STATUSES = ("Rejected", "Void")
CHANGE_ORDER_KNOWN_STATUSES = (
    *CHANGE_ORDER_ACTIVE_STATUSES,
    *CHANGE_ORDER_APPROVED_STATUSES,
    *CHANGE_ORDER_REJECTED_STATUSES,
)
ATTENTION_LIMIT = 10
UPCOMING_TASK_LIMIT = 8
RECENT_DOCUMENT_LIMIT = 8
RECENT_UPDATE_LIMIT = 8
DESCRIPTION_LIMIT = 500


def _count_when(condition):
    return func.sum(case((condition, 1), else_=0))


def _integer(value) -> int:
    return int(value or 0)


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _schedule_summary(
    db: Session,
    project_id: int,
    as_of_text: str,
    upcoming_end_text: str,
) -> dict:
    row = (
        db.query(
            func.count(Task.id),
            func.min(Task.start_date),
            func.max(Task.end_date),
            _count_when(Task.end_date < as_of_text),
            _count_when(
                Task.start_date.between(as_of_text, upcoming_end_text)
            ),
        )
        .filter(Task.project_id == project_id)
        .one()
    )
    return {
        "task_count": _integer(row[0]),
        "planned_start": row[1],
        "planned_finish": row[2],
        "past_planned_finish_count": _integer(row[3]),
        "upcoming_start_count": _integer(row[4]),
    }


def _rfi_summary(
    db: Session,
    project_id: int,
    as_of_text: str,
    upcoming_end_text: str,
) -> dict:
    is_open = RFI.status.in_(RFI_OPEN_STATUSES)
    row = (
        db.query(
            func.count(RFI.id),
            _count_when(is_open),
            _count_when(
                is_open
                & RFI.due_date.is_not(None)
                & (RFI.due_date < as_of_text)
            ),
            _count_when(
                is_open
                & RFI.due_date.between(as_of_text, upcoming_end_text)
            ),
        )
        .filter(RFI.project_id == project_id)
        .one()
    )
    return {
        "total": _integer(row[0]),
        "open": _integer(row[1]),
        "overdue": _integer(row[2]),
        "due_soon": _integer(row[3]),
    }


def _submittal_summary(
    db: Session,
    project_id: int,
    as_of_text: str,
    upcoming_end_text: str,
) -> dict:
    is_pending = Submittal.status.in_(SUBMITTAL_PENDING_STATUSES)
    row = (
        db.query(
            func.count(Submittal.id),
            _count_when(is_pending),
            _count_when(
                is_pending
                & Submittal.required_by_date.is_not(None)
                & (Submittal.required_by_date < as_of_text)
            ),
            _count_when(
                is_pending
                & Submittal.required_by_date.between(
                    as_of_text,
                    upcoming_end_text,
                )
            ),
        )
        .filter(Submittal.project_id == project_id)
        .one()
    )
    return {
        "total": _integer(row[0]),
        "pending": _integer(row[1]),
        "overdue": _integer(row[2]),
        "due_soon": _integer(row[3]),
    }


def _punch_item_summary(
    db: Session,
    project_id: int,
    as_of_text: str,
    trailing_start_text: str,
) -> dict:
    is_open = PunchItem.status.in_(PUNCH_OPEN_STATUSES)
    is_completed = PunchItem.status.in_(PUNCH_COMPLETED_STATUSES)
    row = (
        db.query(
            func.count(PunchItem.id),
            _count_when(is_open),
            _count_when(
                is_open
                & PunchItem.due_date.is_not(None)
                & (PunchItem.due_date < as_of_text)
            ),
            _count_when(
                is_completed
                & PunchItem.completed_date.between(
                    trailing_start_text,
                    as_of_text,
                )
            ),
        )
        .filter(PunchItem.project_id == project_id)
        .one()
    )
    return {
        "total": _integer(row[0]),
        "open": _integer(row[1]),
        "overdue": _integer(row[2]),
        "completed_last_7_days": _integer(row[3]),
    }


def _change_order_summary(db: Session, project_id: int) -> dict:
    is_active = ChangeOrder.status.in_(CHANGE_ORDER_ACTIVE_STATUSES)
    is_approved = ChangeOrder.status.in_(CHANGE_ORDER_APPROVED_STATUSES)
    is_rejected = ChangeOrder.status.in_(CHANGE_ORDER_REJECTED_STATUSES)
    row = (
        db.query(
            func.count(ChangeOrder.id),
            _count_when(is_active),
            _count_when(is_approved),
            _count_when(is_rejected),
            _count_when(~ChangeOrder.status.in_(CHANGE_ORDER_KNOWN_STATUSES)),
            func.coalesce(
                func.sum(
                    case(
                        (is_active, ChangeOrder.proposed_amount),
                        else_=Decimal("0.00"),
                    )
                ),
                Decimal("0.00"),
            ),
            func.coalesce(
                func.sum(
                    case(
                        (is_approved, ChangeOrder.approved_amount),
                        else_=Decimal("0.00"),
                    )
                ),
                Decimal("0.00"),
            ),
        )
        .filter(ChangeOrder.project_id == project_id)
        .one()
    )
    return {
        "total": _integer(row[0]),
        "active": _integer(row[1]),
        "approved": _integer(row[2]),
        "rejected": _integer(row[3]),
        "unknown_status": _integer(row[4]),
        "active_value": _money(row[5]),
        "approved_value": _money(row[6]),
    }


def _daily_log_summary(
    db: Session,
    project_id: int,
    as_of_text: str,
    trailing_start_text: str,
) -> dict:
    row = (
        db.query(
            func.count(DailyLog.id),
            func.max(DailyLog.date),
            _count_when(DailyLog.date == as_of_text),
            func.coalesce(
                func.sum(
                    case(
                        (DailyLog.date == as_of_text, DailyLog.manpower),
                        else_=0,
                    )
                ),
                0,
            ),
            _count_when(
                DailyLog.date.between(trailing_start_text, as_of_text)
            ),
        )
        .filter(DailyLog.project_id == project_id)
        .one()
    )
    return {
        "total": _integer(row[0]),
        "latest_log_date": row[1],
        "today_count": _integer(row[2]),
        "today_manpower": _integer(row[3]),
        "last_7_days_count": _integer(row[4]),
    }


def _document_summary(
    db: Session,
    project_id: int,
    utc_start: datetime,
    utc_end: datetime,
) -> dict:
    row = (
        db.query(
            func.count(Attachment.id),
            _count_when(
                (Attachment.created_at >= utc_start)
                & (Attachment.created_at < utc_end)
            ),
        )
        .filter(Attachment.project_id == project_id)
        .one()
    )
    recent_rows = (
        db.query(
            Attachment.id,
            Attachment.parent_type,
            Attachment.parent_id,
            Attachment.original_filename,
            Attachment.size_bytes,
            Attachment.created_at,
        )
        .filter(Attachment.project_id == project_id)
        .order_by(Attachment.created_at.desc(), Attachment.id.desc())
        .limit(RECENT_DOCUMENT_LIMIT)
        .all()
    )
    return {
        "total": _integer(row[0]),
        "uploaded_last_7_days": _integer(row[1]),
        "recent": [
            {
                "id": item.id,
                "parent_type": item.parent_type,
                "parent_id": item.parent_id,
                "filename": item.original_filename,
                "file_size": item.size_bytes,
                "created_at": _aware_utc(item.created_at),
            }
            for item in recent_rows
        ],
    }


def _attention_items(
    db: Session,
    project_id: int,
    as_of_text: str,
) -> list[dict]:
    sources = (
        select(
            literal("rfi").label("resource_type"),
            RFI.id.label("record_id"),
            RFI.number.label("identifier"),
            func.substr(RFI.subject, 1, DESCRIPTION_LIMIT).label("title"),
            RFI.due_date.label("due_date"),
            literal("Overdue").label("reason"),
            literal("overdue").label("severity"),
            literal("rfis").label("target_page"),
            literal(0).label("severity_rank"),
        ).where(
            RFI.project_id == project_id,
            RFI.status.in_(RFI_OPEN_STATUSES),
            RFI.due_date.is_not(None),
            RFI.due_date < as_of_text,
        ),
        select(
            literal("submittal").label("resource_type"),
            Submittal.id.label("record_id"),
            Submittal.number.label("identifier"),
            func.substr(
                Submittal.title,
                1,
                DESCRIPTION_LIMIT,
            ).label("title"),
            Submittal.required_by_date.label("due_date"),
            literal("Overdue").label("reason"),
            literal("overdue").label("severity"),
            literal("submittals").label("target_page"),
            literal(0).label("severity_rank"),
        ).where(
            Submittal.project_id == project_id,
            Submittal.status.in_(SUBMITTAL_PENDING_STATUSES),
            Submittal.required_by_date.is_not(None),
            Submittal.required_by_date < as_of_text,
        ),
        select(
            literal("punch_item").label("resource_type"),
            PunchItem.id.label("record_id"),
            PunchItem.number.label("identifier"),
            func.substr(
                PunchItem.description,
                1,
                DESCRIPTION_LIMIT,
            ).label("title"),
            PunchItem.due_date.label("due_date"),
            literal("Overdue").label("reason"),
            literal("overdue").label("severity"),
            literal("punch-items").label("target_page"),
            literal(0).label("severity_rank"),
        ).where(
            PunchItem.project_id == project_id,
            PunchItem.status.in_(PUNCH_OPEN_STATUSES),
            PunchItem.due_date.is_not(None),
            PunchItem.due_date < as_of_text,
        ),
        select(
            literal("task").label("resource_type"),
            Task.id.label("record_id"),
            (literal("Task ") + cast(Task.id, String)).label("identifier"),
            func.coalesce(
                func.substr(Task.name, 1, DESCRIPTION_LIMIT),
                literal("Task"),
            ).label("title"),
            Task.end_date.label("due_date"),
            literal("Past planned finish").label("reason"),
            literal("informational").label("severity"),
            literal("schedule").label("target_page"),
            literal(2).label("severity_rank"),
        ).where(
            Task.project_id == project_id,
            Task.end_date.is_not(None),
            Task.end_date < as_of_text,
        ),
    )
    combined = union_all(*sources).subquery()
    rows = db.execute(
        select(
            combined.c.resource_type,
            combined.c.record_id,
            combined.c.identifier,
            combined.c.title,
            combined.c.due_date,
            combined.c.reason,
            combined.c.severity,
            combined.c.target_page,
        )
        .order_by(
            combined.c.severity_rank,
            combined.c.due_date.is_(None),
            combined.c.due_date,
            combined.c.resource_type,
            combined.c.record_id,
        )
        .limit(ATTENTION_LIMIT)
    ).mappings()
    return [dict(row) for row in rows]


def _upcoming_tasks(
    db: Session,
    project_id: int,
    as_of_text: str,
    upcoming_end_text: str,
) -> list[dict]:
    rows = (
        db.query(
            Task.id,
            func.substr(Task.name, 1, DESCRIPTION_LIMIT).label("name"),
            Task.start_date,
            Task.end_date,
            Task.duration,
        )
        .filter(
            Task.project_id == project_id,
            Task.start_date.between(as_of_text, upcoming_end_text),
        )
        .order_by(
            Task.start_date,
            Task.order_index.is_(None),
            Task.order_index,
            Task.id,
        )
        .limit(UPCOMING_TASK_LIMIT)
        .all()
    )
    return [
        {
            "id": item.id,
            "name": item.name or f"Task {item.id}",
            "start_date": item.start_date,
            "end_date": item.end_date,
            "duration": item.duration,
        }
        for item in rows
    ]


def _recent_updates(db: Session, project_id: int) -> list[dict]:
    attachment_target = case(
        (Attachment.parent_type == "project", "project"),
        (Attachment.parent_type == "daily_log", "daily-logs"),
        (Attachment.parent_type == "rfi", "rfis"),
        (Attachment.parent_type == "submittal", "submittals"),
        (Attachment.parent_type == "punch_item", "punch-items"),
        (Attachment.parent_type == "change_order", "change-orders"),
        else_="project",
    )
    sources = (
        select(
            literal("rfi").label("resource_type"),
            RFI.id.label("record_id"),
            RFI.number.label("identifier"),
            func.substr(RFI.subject, 1, DESCRIPTION_LIMIT).label(
                "description"
            ),
            RFI.updated_at.label("updated_at"),
            literal("rfis").label("target_page"),
        ).where(RFI.project_id == project_id),
        select(
            literal("submittal").label("resource_type"),
            Submittal.id.label("record_id"),
            Submittal.number.label("identifier"),
            func.substr(Submittal.title, 1, DESCRIPTION_LIMIT).label(
                "description"
            ),
            Submittal.updated_at.label("updated_at"),
            literal("submittals").label("target_page"),
        ).where(Submittal.project_id == project_id),
        select(
            literal("punch_item").label("resource_type"),
            PunchItem.id.label("record_id"),
            PunchItem.number.label("identifier"),
            func.substr(
                PunchItem.description,
                1,
                DESCRIPTION_LIMIT,
            ).label("description"),
            PunchItem.updated_at.label("updated_at"),
            literal("punch-items").label("target_page"),
        ).where(PunchItem.project_id == project_id),
        select(
            literal("change_order").label("resource_type"),
            ChangeOrder.id.label("record_id"),
            ChangeOrder.co_number.label("identifier"),
            func.substr(
                func.coalesce(
                    ChangeOrder.title,
                    ChangeOrder.description,
                    ChangeOrder.co_number,
                ),
                1,
                DESCRIPTION_LIMIT,
            ).label("description"),
            ChangeOrder.updated_at.label("updated_at"),
            literal("change-orders").label("target_page"),
        ).where(ChangeOrder.project_id == project_id),
        select(
            literal("attachment").label("resource_type"),
            Attachment.id.label("record_id"),
            Attachment.original_filename.label("identifier"),
            Attachment.original_filename.label("description"),
            Attachment.created_at.label("updated_at"),
            attachment_target.label("target_page"),
        ).where(Attachment.project_id == project_id),
    )
    combined = union_all(*sources).subquery()
    rows = db.execute(
        select(
            combined.c.resource_type,
            combined.c.record_id,
            combined.c.identifier,
            combined.c.description,
            combined.c.updated_at,
            combined.c.target_page,
        )
        .order_by(
            combined.c.updated_at.desc(),
            combined.c.resource_type,
            combined.c.record_id,
        )
        .limit(RECENT_UPDATE_LIMIT)
    ).mappings()
    return [
        {
            **dict(row),
            "updated_at": _aware_utc(row.updated_at),
        }
        for row in rows
    ]


def get_project_dashboard(
    db: Session,
    project: Project,
    as_of: date,
) -> dict:
    trailing_start = as_of - timedelta(days=6)
    upcoming_end = as_of + timedelta(days=7)
    as_of_text = as_of.isoformat()
    trailing_start_text = trailing_start.isoformat()
    upcoming_end_text = upcoming_end.isoformat()
    utc_start = datetime.combine(
        trailing_start,
        time.min,
        tzinfo=timezone.utc,
    )
    utc_end = datetime.combine(
        as_of + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    return {
        "as_of": as_of,
        "generated_at": datetime.now(timezone.utc),
        "project": {
            "id": project.id,
            "name": project.name,
        },
        "schedule": _schedule_summary(
            db,
            project.id,
            as_of_text,
            upcoming_end_text,
        ),
        "schedule_health": get_schedule_health(
            db,
            project_id=project.id,
        ),
        "rfis": _rfi_summary(
            db,
            project.id,
            as_of_text,
            upcoming_end_text,
        ),
        "submittals": _submittal_summary(
            db,
            project.id,
            as_of_text,
            upcoming_end_text,
        ),
        "punch_items": _punch_item_summary(
            db,
            project.id,
            as_of_text,
            trailing_start_text,
        ),
        "change_orders": _change_order_summary(db, project.id),
        "daily_logs": _daily_log_summary(
            db,
            project.id,
            as_of_text,
            trailing_start_text,
        ),
        "documents": _document_summary(
            db,
            project.id,
            utc_start,
            utc_end,
        ),
        "attention_items": _attention_items(
            db,
            project.id,
            as_of_text,
        ),
        "upcoming_tasks": _upcoming_tasks(
            db,
            project.id,
            as_of_text,
            upcoming_end_text,
        ),
        "recent_updates": _recent_updates(db, project.id),
    }
