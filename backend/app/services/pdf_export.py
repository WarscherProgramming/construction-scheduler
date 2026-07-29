from html import escape
from pathlib import Path
import re
import tempfile
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


_UNSAFE_FILENAME_CHARACTER = re.compile(r"[^A-Za-z0-9._-]+")


def escape_reportlab_text(value: object) -> str:
    return escape(str(value), quote=True)


def safe_export_filename(project_name: str, project_id: int) -> str:
    normalized = unicodedata.normalize("NFKC", project_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = _UNSAFE_FILENAME_CHARACTER.sub("_", ascii_name).strip("._")
    safe_name = safe_name[:80].rstrip("._")
    if not safe_name:
        safe_name = f"project-{project_id}"
    return f"{safe_name}_schedule.pdf"


def remove_export_file(file_path: str | Path) -> None:
    Path(file_path).unlink(missing_ok=True)


def build_project_schedule_pdf(project, tasks) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file_path = Path(handle.name)
    handle.close()

    try:
        document = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(letter),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]
        body_style.wordWrap = "CJK"

        elements = [
            Paragraph(
                f"Schedule: {escape_reportlab_text(project.name)}",
                styles["Title"],
            ),
            Spacer(1, 12),
        ]

        data = [
            [
                "Task ID",
                "Task",
                "Duration",
                "Start",
                "End",
                "Predecessor",
            ]
        ]
        task_map = {task.id: task for task in tasks}

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

            task_name = f"{'    ' * depth}{task.name or ''}"
            data.append(
                [
                    task.id,
                    Paragraph(
                        escape_reportlab_text(task_name),
                        body_style,
                    ),
                    task.duration,
                    escape_reportlab_text(task.start_date or "-"),
                    escape_reportlab_text(task.end_date or "-"),
                    escape_reportlab_text(task.predecessor or "-"),
                ]
            )

        table = Table(
            data,
            colWidths=[48, 280, 60, 82, 82, 100],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
        document.build(elements)
        return file_path
    except Exception:
        remove_export_file(file_path)
        raise
