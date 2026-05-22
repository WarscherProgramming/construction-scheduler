
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
from app.db.database import SessionLocal
from app.models.task import Task
from app.models.project import Project
from fastapi import HTTPException
from app.core.security import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_project_owner(project_id: int, user_id: int, db: Session):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project"
        )

    return project


@router.get("/projects/{project_id}/export/pdf")
def export_project_pdf(project_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = verify_project_owner(project_id, current_user["id"], db)

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.id)
        .all()
    )

    file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file_path = file.name
    file.close()

    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(letter),
    )

    styles = getSampleStyleSheet()

    elements = [
        Paragraph(f"Schedule: {project.name}", styles["Title"]),
        Spacer(1, 12),
    ]

    data = [["Index", "Task", "Duration", "Start", "End", "Predecessor"]]

    for index, task in enumerate(tasks, start=1):
        data.append([
            index,
            task.name,
            task.duration,
            task.start_date or "-",
            task.end_date or "-",
            task.predecessor or "-",
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{project.name}_schedule.pdf",
    )