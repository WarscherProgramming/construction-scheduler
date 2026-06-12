from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re
from app.db.database import SessionLocal
from app.models.task import Task
from app.core.security import get_current_user
from fastapi import HTTPException
from app.models.project import Project

router = APIRouter()

today = datetime.today()
PROJECT_START = datetime(today.year, today.month, today.day)


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

def task_to_dict(task):
    return {
        "id": task.id,
        "name": task.name,
        "duration": task.duration,
        "manual_start_date": task.manual_start_date,
        "predecessor": task.predecessor,
        "start_date": task.start_date,
        "end_date": task.end_date,
        "project_id": task.project_id,
    }


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


@router.get("/projects/{project_id}/tasks")
def get_tasks(project_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    verify_project_owner(project_id, current_user["id"], db)
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )

    return {"tasks": [task_to_dict(task) for task in tasks]}


@router.post("/projects/{project_id}/tasks")
def create_task(project_id: int, task: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    verify_project_owner(project_id, current_user["id"], db)
    new_task = Task(
        project_id=project_id,
        name=task["name"],
        duration=task["duration"],
        manual_start_date=task.get("manual_start_date"),
        predecessor=task.get("predecessor"),
    )

    db.add(new_task)
    db.commit()

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.id)
        .all()
    )

    calculate_schedule(tasks)

    db.commit()

    return {"tasks": [task_to_dict(task) for task in tasks]}

@router.put("/projects/{project_id}/tasks/reorder")
def reorder_tasks(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    task_ids = payload["task_ids"]

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

@router.put("/projects/{project_id}/tasks/{task_id}")
def update_task(
    project_id: int,
    task_id: int,
    updated_task: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if task:
        task.name = updated_task.get("name", task.name)
        task.duration = updated_task.get("duration", task.duration)
        task.manual_start_date = updated_task.get(
            "manual_start_date", task.manual_start_date
        )
        task.predecessor = updated_task.get("predecessor", task.predecessor)

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.id)
        .all()
    )

    calculate_schedule(tasks)

    db.commit()

    return {"tasks": [task_to_dict(task) for task in tasks]}


@router.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    verify_project_owner(project_id, current_user["id"], db)
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
        .order_by(Task.id)
        .all()
    )

    calculate_schedule(tasks)

    db.commit()

    return {"tasks": [task_to_dict(task) for task in tasks]}

