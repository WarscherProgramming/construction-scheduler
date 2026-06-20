from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re
from app.api.dependencies import get_db, get_owned_project
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

today = datetime.today()
PROJECT_START = datetime(today.year, today.month, today.day)


def parse_predecessor(value):
    if not value:
        return None, "FS", 0

    value = str(value).replace(" ", "").upper()

    match = re.match(r"^(\d+)(SS)?(?:\+(\d+)D?)?$", value)

    if not match:
        return None, "FS", 0

    pred_index = int(match.group(1))
    relation = "SS" if match.group(2) else "FS"
    lag = int(match.group(3)) if match.group(3) else 0

    return pred_index, relation, lag

def is_workday(date):
    return date.weekday() < 5

def next_workday(date):
    while not is_workday(date):
        date += timedelta(days=1)
    return date


def add_workdays(start_date, duration):
    current_date = next_workday(start_date)
    days_added = 1

    while days_added < duration:
        current_date += timedelta(days=1)

        if is_workday(current_date):
            days_added += 1

    return current_date

def get_indent_level(task):
    name = task.name or ""
    leading_spaces = len(name) - len(name.lstrip(" "))
    return leading_spaces // 4

def calculate_schedule(task_list):
    index_map = {
        index + 1: task
        for index, task in enumerate(task_list)
    }

    for task in task_list:
        task.start_date = None
        task.end_date = None

    for _ in range(len(task_list)):
        for task in task_list:
            pred_index, relation, lag = parse_predecessor(task.predecessor)

            if not pred_index:
                if task.manual_start_date:
                    start_date = datetime.strptime(
                        task.manual_start_date, "%Y-%m-%d"
                    )
                else:
                    start_date = PROJECT_START
            else:
                predecessor = index_map.get(pred_index)

                if not predecessor or not predecessor.end_date:
                    continue

                if relation == "SS":
                    start_date = datetime.strptime(
                        predecessor.start_date, "%Y-%m-%d"
                    ) + timedelta(days=lag)
                else:
                    start_date = datetime.strptime(
                        predecessor.end_date, "%Y-%m-%d"
                    ) + timedelta(days=1 + lag)

                    start_date = next_workday(start_date)

            start_date = next_workday(start_date)
            end_date = add_workdays(start_date, task.duration)

            task.start_date = start_date.strftime("%Y-%m-%d")
            task.end_date = end_date.strftime("%Y-%m-%d")

    return task_list

def rollup_parent_tasks(task_list):
    for index, task in enumerate(task_list):
        current_level = get_indent_level(task)

        child_tasks = []

        for next_task in task_list[index + 1:]:
            next_level = get_indent_level(next_task)

            if next_level <= current_level:
                break

            if next_level == current_level + 1:
                child_tasks.append(next_task)

        if child_tasks:
            child_start_dates = [
                datetime.strptime(child.start_date, "%Y-%m-%d")
                for child in child_tasks
                if child.start_date
            ]

            child_end_dates = [
                datetime.strptime(child.end_date, "%Y-%m-%d")
                for child in child_tasks
                if child.end_date
            ]

            if child_start_dates and child_end_dates:
                task.start_date = min(child_start_dates).strftime("%Y-%m-%d")
                task.end_date = max(child_end_dates).strftime("%Y-%m-%d")
                task.duration = len(child_end_dates)


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

    calculate_schedule(tasks)
    rollup_parent_tasks(tasks)

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

    calculate_schedule(tasks)
    rollup_parent_tasks(tasks)

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

    calculate_schedule(tasks)
    rollup_parent_tasks(tasks)

    db.commit()

    return {"tasks": tasks}

