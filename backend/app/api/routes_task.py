from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from app.api.dependencies import get_db, get_owned_project
from app.domain.scheduling import ScheduleTask, calculate_schedule
from app.models.task import Task
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskReorderRequest,
    TaskUpdate,
)

router = APIRouter()


def recalculate_schedule(tasks: list[Task]) -> None:
    schedule = calculate_schedule(
        [
            ScheduleTask(
                id=task.id,
                name=task.name or "",
                duration=task.duration,
                predecessor=task.predecessor,
                manual_start_date=task.manual_start_date,
            )
            for task in tasks
        ],
        project_start=date.today(),
    )

    for task, scheduled_task in zip(tasks, schedule, strict=True):
        task.start_date = scheduled_task.start_date
        task.end_date = scheduled_task.end_date
        task.duration = scheduled_task.duration


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def get_tasks(
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

    return {"tasks": tasks}


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskListResponse,
    status_code=201,
)
def create_task(
    project_id: int,
    task: TaskCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_task = Task(
        project_id=project_id,
        **task.model_dump(),
    )

    db.add(new_task)
    db.commit()

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    recalculate_schedule(tasks)

    db.commit()

    return {"tasks": tasks}

@router.put(
    "/projects/{project_id}/tasks/reorder",
    response_model=MessageResponse,
)
def reorder_tasks(
    project_id: int,
    payload: TaskReorderRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    task_ids = payload.task_ids

    for index, task_id in enumerate(task_ids, start=1):
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.project_id == project_id)
            .first()
        )

        if task:
            task.order_index = index

    db.commit()

    return {"message": "Tasks reordered"}

@router.put(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskListResponse,
)
def update_task(
    project_id: int,
    task_id: int,
    updated_task: TaskUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if task:
        for field, value in updated_task.model_dump(exclude_unset=True).items():
            setattr(task, field, value)

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    recalculate_schedule(tasks)

    db.commit()

    return {"tasks": tasks}


@router.delete(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskListResponse,
)
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if task:
        db.delete(task)
        db.commit()

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    recalculate_schedule(tasks)

    db.commit()

    return {"tasks": tasks}

