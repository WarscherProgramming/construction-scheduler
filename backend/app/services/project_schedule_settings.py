from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.project_schedule_settings import ProjectScheduleSettings


def create_project_schedule_settings(
    db: Session,
    project_id: int,
    *,
    schedule_start_date: date,
) -> ProjectScheduleSettings:
    settings = ProjectScheduleSettings(
        project_id=project_id,
        schedule_start_date=schedule_start_date.isoformat(),
        data_date=schedule_start_date.isoformat(),
    )
    db.add(settings)
    db.flush()
    return settings


def server_schedule_start_date() -> date:
    """Choose a new project's anchor once, in the server's local date."""
    return datetime.now().astimezone().date()


def get_project_schedule_settings(
    db: Session,
    project_id: int,
) -> ProjectScheduleSettings:
    settings = db.get(ProjectScheduleSettings, project_id)
    if settings is None:
        raise RuntimeError("Project schedule settings are missing")
    return settings


def get_project_schedule_start(db: Session, project_id: int) -> date:
    settings = get_project_schedule_settings(db, project_id)
    return date.fromisoformat(settings.schedule_start_date)


def get_project_schedule_dates(
    db: Session,
    project_id: int,
) -> tuple[date, date]:
    settings = get_project_schedule_settings(db, project_id)
    return (
        date.fromisoformat(settings.schedule_start_date),
        date.fromisoformat(settings.data_date),
    )
