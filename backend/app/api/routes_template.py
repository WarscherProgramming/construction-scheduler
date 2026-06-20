
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_owned_project
from app.models.task import Task
from app.models.template import ScheduleTemplate, ScheduleTemplateTask
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
)
from app.services.task_scheduling import recalculate_schedule

router = APIRouter()


@router.get("/templates", response_model=TemplateListResponse)
def get_templates(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    templates = db.query(ScheduleTemplate).order_by(ScheduleTemplate.id).all()

    return {
        "templates": [
            {"id": template.id, "name": template.name}
            for template in templates
        ]
    }


@router.post(
    "/projects/{project_id}/templates",
    response_model=TemplateResponse,
    status_code=201,
)
def save_project_as_template(
    project_id: int,
    template: TemplateCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    new_template = ScheduleTemplate(name=template.name)

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    template_task_map = {}

    for index, task in enumerate(tasks, start=1):
        template_task = ScheduleTemplateTask(
            template_id=new_template.id,
            name=task.name,
            duration=task.duration,
            dependency_type=task.dependency_type,
            lag_days=task.lag_days,
            order_index=index,
            manual_start_date=task.manual_start_date,
        )

        db.add(template_task)
        db.flush()
        template_task_map[task.id] = template_task

    for task in tasks:
        template_task = template_task_map[task.id]
        template_task.predecessor_template_task_id = (
            template_task_map[task.predecessor_task_id].id
            if task.predecessor_task_id in template_task_map
            else None
        )
        template_task.parent_template_task_id = (
            template_task_map[task.parent_task_id].id
            if task.parent_task_id in template_task_map
            else None
        )

    db.commit()

    return {
        "id": new_template.id,
        "name": new_template.name,
    }


@router.post(
    "/projects/{project_id}/templates/{template_id}/apply",
    response_model=MessageResponse,
)
def apply_template_to_project(
    project_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    template_tasks = (
        db.query(ScheduleTemplateTask)
        .filter(ScheduleTemplateTask.template_id == template_id)
        .order_by(ScheduleTemplateTask.order_index, ScheduleTemplateTask.id)
        .all()
    )

    project_task_map = {}
    current_max_order = (
        db.query(func.max(Task.order_index))
        .filter(Task.project_id == project_id)
        .scalar()
        or 0
    )

    for index, template_task in enumerate(template_tasks, start=1):
        new_task = Task(
            project_id=project_id,
            name=template_task.name,
            duration=template_task.duration,
            dependency_type=template_task.dependency_type,
            lag_days=template_task.lag_days,
            order_index=current_max_order + index,
            manual_start_date=template_task.manual_start_date,
        )

        db.add(new_task)
        db.flush()
        project_task_map[template_task.id] = new_task

    for template_task in template_tasks:
        new_task = project_task_map[template_task.id]
        predecessor = project_task_map.get(
            template_task.predecessor_template_task_id
        )
        parent = project_task_map.get(template_task.parent_template_task_id)
        new_task.predecessor_task_id = predecessor.id if predecessor else None
        new_task.parent_task_id = parent.id if parent else None

    recalculate_schedule(list(project_task_map.values()))

    db.commit()

    return {"message": "Template applied"}
