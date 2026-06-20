
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
from app.api.dependencies import get_db, get_owned_project
from app.models.task import Task
from app.models.project import Project

router = APIRouter()


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
    task_map = {task.id: task for task in tasks}

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

    data = [["Task ID", "Task", "Duration", "Start", "End", "Predecessor"]]

    for task in tasks:
        depth = 0
        parent_id = task.parent_task_id
        visited = set()

        while parent_id is not None and parent_id not in visited:
            visited.add(parent_id)
            parent = task_map.get(parent_id)
            if parent is None:
                break
            depth += 1
            parent_id = parent.parent_task_id

        data.append([
            task.id,
            f"{'    ' * depth}{task.name}",
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
