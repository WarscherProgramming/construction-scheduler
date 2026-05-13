
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

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/projects/{project_id}/export/pdf")
def export_project_pdf(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()

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
        Paragraph(f"Schedule: {project.name if project else 'Project'}", styles["Title"]),
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
        filename=f"{project.name if project else 'schedule'}_schedule.pdf",
    )