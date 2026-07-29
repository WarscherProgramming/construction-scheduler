
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.dependencies import get_db, get_owned_project
from app.models.task import Task
from app.models.project import Project
from app.services.pdf_export import (
    build_project_schedule_pdf,
    remove_export_file,
    safe_export_filename,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
        .all()
    )

    try:
        file_path = build_project_schedule_pdf(project, tasks)
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
