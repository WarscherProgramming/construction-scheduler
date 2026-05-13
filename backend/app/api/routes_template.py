
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.task import Task
from app.models.template import ScheduleTemplate, ScheduleTemplateTask

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/templates")
def get_templates(db: Session = Depends(get_db)):
    templates = db.query(ScheduleTemplate).order_by(ScheduleTemplate.id).all()

    return {
        "templates": [
            {"id": template.id, "name": template.name}
            for template in templates
        ]
    }


@router.post("/projects/{project_id}/templates")
def save_project_as_template(
    project_id: int,
    template: dict,
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.id)
        .all()
    )

    new_template = ScheduleTemplate(name=template["name"])

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    for task in tasks:
        template_task = ScheduleTemplateTask(
            template_id=new_template.id,
            name=task.name,
            duration=task.duration,
            predecessor=task.predecessor,
            manual_start_date=task.manual_start_date,
        )

        db.add(template_task)

    db.commit()

    return {
        "id": new_template.id,
        "name": new_template.name,
    }


@router.post("/projects/{project_id}/templates/{template_id}/apply")
def apply_template_to_project(
    project_id: int,
    template_id: int,
    db: Session = Depends(get_db),
):
    template_tasks = (
        db.query(ScheduleTemplateTask)
        .filter(ScheduleTemplateTask.template_id == template_id)
        .order_by(ScheduleTemplateTask.id)
        .all()
    )

    for template_task in template_tasks:
        new_task = Task(
            project_id=project_id,
            name=template_task.name,
            duration=template_task.duration,
            predecessor=template_task.predecessor,
            manual_start_date=template_task.manual_start_date,
        )

        db.add(new_task)

    db.commit()

    return {"message": "Template applied"}