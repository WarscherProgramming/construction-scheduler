
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.dependencies import (
    CollectionPage,
    PositiveId,
    get_collection_page,
    get_db,
    get_owned_project,
)
from app.models.task import Task, TaskDependency
from app.models.template import (
    ScheduleTemplate,
    ScheduleTemplateTask,
    ScheduleTemplateTaskDependency,
)
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
)
from app.services.task_scheduling import (
    lock_project_schedule,
    recalculate_schedule,
)
from app.services.project_schedule_settings import get_project_schedule_dates
from app.services.task_validation import (
    validate_hierarchy_order,
    validate_schedule_structure,
)
from app.services.task_dependencies import task_dependencies

router = APIRouter()


@router.get("/templates", response_model=TemplateListResponse)
def get_templates(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: CollectionPage = Depends(get_collection_page),
):
    templates = (
        db.query(ScheduleTemplate)
        .filter(ScheduleTemplate.user_id == current_user["id"])
        .order_by(ScheduleTemplate.id)
        .offset(page.offset)
        .limit(page.limit)
        .all()
    )

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

    new_template = ScheduleTemplate(
        name=template.name,
        user_id=project.user_id,
    )

    db.add(new_template)
    db.flush()

    template_task_map = {}

    for index, task in enumerate(tasks, start=1):
        template_task = ScheduleTemplateTask(
            template_id=new_template.id,
            name=task.name,
            duration=task.duration,
            dependency_type=task.dependency_type,
            lag_days=task.lag_days,
            order_index=index,
            # Templates preserve structure and relative logic, not absolute
            # dates from the source project's calendar position.
            manual_start_date=None,
            is_milestone=task.is_milestone,
            constraint_type=task.constraint_type,
            constraint_date=task.constraint_date,
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
        for dependency in task_dependencies(task):
            predecessor = template_task_map.get(
                dependency.predecessor_task_id
            )
            if predecessor is not None:
                db.add(
                    ScheduleTemplateTaskDependency(
                        template_id=new_template.id,
                        template_task_id=template_task.id,
                        predecessor_template_task_id=predecessor.id,
                        dependency_type=dependency.dependency_type,
                        lag_days=dependency.lag_days,
                    )
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
    template_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    lock_project_schedule(db, project_id)
    template = (
        db.query(ScheduleTemplate)
        .filter(
            ScheduleTemplate.id == template_id,
            ScheduleTemplate.user_id == project.user_id,
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

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
            manual_start_date=None,
            is_milestone=template_task.is_milestone,
            constraint_type=template_task.constraint_type,
            constraint_date=template_task.constraint_date,
            progress_status="not_started",
            percent_complete=0,
            remaining_duration=(
                0 if template_task.is_milestone else template_task.duration
            ),
            actual_start_date=None,
            actual_finish_date=None,
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
        for dependency in template_task.dependencies:
            predecessor = project_task_map.get(
                dependency.predecessor_template_task_id
            )
            if predecessor is not None:
                new_task.dependencies.append(
                    TaskDependency(
                        project_id=project_id,
                        predecessor_task_id=predecessor.id,
                        dependency_type=dependency.dependency_type,
                        lag_days=dependency.lag_days,
                    )
                )

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )
    try:
        validate_hierarchy_order(tasks, [task.id for task in tasks])
        validate_schedule_structure(tasks)
        project_start, data_date = get_project_schedule_dates(db, project_id)
        recalculate_schedule(
            tasks,
            project_start=project_start,
            data_date=data_date,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "Template applied"}
