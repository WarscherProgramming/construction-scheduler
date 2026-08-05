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

from app.services.task_scheduling import schedule_metadata


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


def safe_executive_report_filename(project_name: str, project_id: int) -> str:
    schedule_name = safe_export_filename(project_name, project_id)
    return schedule_name.removesuffix("_schedule.pdf") + "_schedule_executive.pdf"


def remove_export_file(file_path: str | Path) -> None:
    Path(file_path).unlink(missing_ok=True)


def build_project_schedule_pdf(
    project,
    tasks,
    *,
    data_date: str | None = None,
) -> Path:
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
            Paragraph(
                f"Data Date: {escape_reportlab_text(data_date or '-')}",
                styles["BodyText"],
            ),
            Spacer(1, 12),
        ]

        data = [
            [
                "Task ID",
                "Task",
                "Duration",
                "Status",
                "%",
                "Remaining",
                "Forecast Start",
                "Forecast Finish",
                "Actual Start",
                "Actual Finish",
                "Predecessor",
            ]
        ]
        task_map = {task.id: task for task in tasks}
        task_metadata = schedule_metadata(tasks)

        for task, progress in zip(tasks, task_metadata, strict=True):
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
                    progress.progress_status.replace("_", " ").title(),
                    f"{progress.percent_complete}%",
                    (
                        progress.remaining_duration
                        if progress.remaining_duration is not None
                        else "-"
                    ),
                    escape_reportlab_text(task.start_date or "-"),
                    escape_reportlab_text(task.end_date or "-"),
                    escape_reportlab_text(progress.actual_start_date or "-"),
                    escape_reportlab_text(progress.actual_finish_date or "-"),
                    escape_reportlab_text(task.predecessor or "-"),
                ]
            )

        table = Table(
            data,
            colWidths=[36, 148, 42, 66, 32, 46, 62, 62, 62, 62, 72],
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


def build_schedule_executive_pdf(project, health: dict) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file_path = Path(handle.name)
    handle.close()

    try:
        document = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]
        body_style.wordWrap = "CJK"
        summary = health["executive_summary"]
        elements = [
            Paragraph(
                f"Executive Schedule Summary: {escape_reportlab_text(project.name)}",
                styles["Title"],
            ),
            Paragraph(
                f"Schedule Start: {escape_reportlab_text(summary['schedule_start_date'])}"
                f" | Data Date: {escape_reportlab_text(summary['data_date'])}",
                body_style,
            ),
            Paragraph(
                f"Health: {escape_reportlab_text(health['category'].title())}"
                f" - {escape_reportlab_text(health['summary'])}",
                body_style,
            ),
            Spacer(1, 12),
        ]

        metric_rows = [
            ["Metric", "Value"],
            ["Baseline", summary["baseline_name"] or "No active baseline"],
            ["Baseline Finish", summary["baseline_project_finish"] or "-"],
            ["Current Forecast Finish", summary["current_forecast_finish"] or "-"],
            [
                "Finish Variance",
                "Not available"
                if summary["project_finish_variance_workdays"] is None
                else f"{summary['project_finish_variance_workdays']} workdays",
            ],
            ["Leaf Tasks", summary["total_leaf_tasks"]],
            ["Not Started", summary["not_started_tasks"]],
            ["In Progress", summary["in_progress_tasks"]],
            ["Completed", summary["completed_tasks"]],
            ["Slipped", summary["slipped_tasks"]],
            ["Newly Critical", summary["newly_critical_tasks"]],
            ["Negative Float", summary["negative_float_tasks"]],
            ["Out of Sequence", summary["out_of_sequence_tasks"]],
            ["Milestones Due (21 Days)", summary["milestones_due_next_21_days"]],
            ["Blocked Look-Ahead", summary["blocked_look_ahead_items"]],
            ["Committed Look-Ahead", summary["committed_look_ahead_items"]],
            ["Labor Over-Allocation Days", summary["labor_overallocated_days"]],
            ["Equipment Over-Allocation Days", summary["equipment_overallocated_days"]],
            ["Unassigned Executable Tasks", summary["unassigned_executable_tasks"]],
        ]
        metric_table = Table(
            [
                [
                    Paragraph(escape_reportlab_text(row[0]), body_style),
                    Paragraph(escape_reportlab_text(row[1]), body_style),
                ]
                for row in metric_rows
            ],
            colWidths=[250, 250],
            repeatRows=1,
        )
        metric_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.extend([metric_table, Spacer(1, 14)])

        elements.append(Paragraph("Health Reasons", styles["Heading2"]))
        if health["reasons"]:
            for reason in health["reasons"]:
                elements.append(Paragraph(
                    f"{escape_reportlab_text(reason['severity'].title())}: "
                    f"{escape_reportlab_text(reason['label'])}",
                    body_style,
                ))
        else:
            elements.append(Paragraph("No health reasons are active.", body_style))

        elements.extend([Spacer(1, 14), Paragraph("Top Attention Items", styles["Heading2"])])
        if health["top_attention_items"]:
            attention_rows = [["Severity", "Item", "Reason"]]
            for item in health["top_attention_items"]:
                attention_rows.append([
                    item["severity"].title(),
                    item["title"],
                    item["reason"],
                ])
            attention_table = Table(
                [
                    [Paragraph(escape_reportlab_text(value), body_style) for value in row]
                    for row in attention_rows
                ],
                colWidths=[70, 150, 280],
                repeatRows=1,
            )
            attention_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(attention_table)
        else:
            elements.append(Paragraph("No attention items are active.", body_style))

        document.build(elements)
        return file_path
    except Exception:
        remove_export_file(file_path)
        raise
