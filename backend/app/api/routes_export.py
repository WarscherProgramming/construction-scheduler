
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.models.task import Task
from app.models.project import Project
from app.services.project_schedule_settings import (
    get_project_schedule_settings,
)
from app.services.pdf_export import (
    build_schedule_executive_pdf,
    build_project_schedule_pdf,
    remove_export_file,
    safe_executive_report_filename,
    safe_export_filename,
)
from app.services.schedule_health import get_schedule_health

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_EXPORT_TASKS = 5_000


@router.get("/projects/{project_id}/export/pdf")
def export_project_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .limit(MAX_EXPORT_TASKS + 1)
        .all()
    )
    if len(tasks) > MAX_EXPORT_TASKS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Project schedule is too large to export",
        )

    try:
        settings = get_project_schedule_settings(db, project_id)
        file_path = build_project_schedule_pdf(
            project,
            tasks,
            data_date=settings.data_date,
        )
    except Exception as error:
        logger.exception("Project schedule PDF generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate project schedule PDF",
        ) from error

    try:
        return FileResponse(
            str(file_path),
            media_type="application/pdf",
            filename=safe_export_filename(project.name, project.id),
            background=BackgroundTask(remove_export_file, file_path),
        )
    except Exception:
        remove_export_file(file_path)
        raise


@router.get("/projects/{project_id}/reports/schedule-executive.pdf")
def export_schedule_executive_pdf(
    project_id: int,
    baseline_id: Annotated[PositiveId | None, Query()] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    try:
        health = get_schedule_health(
            db,
            project_id=project_id,
            baseline_id=baseline_id,
        )
        file_path = build_schedule_executive_pdf(project, health)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Executive schedule PDF generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate executive schedule report",
        ) from error

    try:
        return FileResponse(
            str(file_path),
            media_type="application/pdf",
            filename=safe_executive_report_filename(project.name, project.id),
            background=BackgroundTask(remove_export_file, file_path),
        )
    except Exception:
        remove_export_file(file_path)
        raise
