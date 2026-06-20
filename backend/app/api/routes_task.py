from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.task import Task
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskReorderRequest,
    TaskUpdate,
    parse_predecessor_reference,
)
from app.services.task_scheduling import recalculate_schedule

router = APIRouter()


def validate_task_reference(
    task_id: int | None,
    *,
    project_id: int,
    db: Session,
    field_name: str,
) -> None:
    if task_id is None:
        return

    exists = (
        db.query(Task.id)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must reference a task in this project",
        )


def validate_parent_assignment(
    task: Task,
    parent_task_id: int | None,
    *,
    project_id: int,
    db: Session,
) -> None:
    validate_task_reference(
        parent_task_id,
        project_id=project_id,
        db=db,
        field_name="parent_task_id",
    )

    if parent_task_id is None:
        return

    if parent_task_id == task.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A task cannot be its own parent",
        )

    visited: set[int] = set()
    current_id = parent_task_id

    while current_id is not None and current_id not in visited:
        if current_id == task.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Parent assignment would create a hierarchy cycle",
            )

        visited.add(current_id)
        current = (
            db.query(Task)
            .filter(Task.id == current_id, Task.project_id == project_id)
            .first()
        )
        current_id = current.parent_task_id if current else None


def validate_dependency_assignment(
    task: Task,
    predecessor_task_id: int | None,
    *,
    project_id: int,
    db: Session,
) -> None:
    validate_task_reference(
        predecessor_task_id,
        project_id=project_id,
        db=db,
        field_name="predecessor_task_id",
    )

    if predecessor_task_id is None:
        return

    if predecessor_task_id == task.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A task cannot depend on itself",
        )

    visited: set[int] = set()
    current_id = predecessor_task_id

    while current_id is not None and current_id not in visited:
        if current_id == task.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dependency assignment would create a cycle",
            )

        visited.add(current_id)
        current = (
            db.query(Task)
            .filter(Task.id == current_id, Task.project_id == project_id)
            .first()
        )
        current_id = current.predecessor_task_id if current else None


def dependency_values(payload: TaskCreate | TaskUpdate) -> dict:
    if "predecessor" in payload.model_fields_set:
        predecessor_task_id, dependency_type, lag_days = (
            parse_predecessor_reference(payload.predecessor)
        )
        return {
            "predecessor_task_id": predecessor_task_id,
            "dependency_type": dependency_type,
            "lag_days": lag_days,
        }

    return {
        field: value
        for field, value in payload.model_dump(
            include={
                "predecessor_task_id",
                "dependency_type",
                "lag_days",
            },
            exclude_unset=True,
        ).items()
    }


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
    values = task.model_dump(
        exclude={
            "predecessor",
            "predecessor_task_id",
            "dependency_type",
            "lag_days",
        }
    )
    values.update(dependency_values(task))

    validate_task_reference(
        values.get("predecessor_task_id"),
        project_id=project_id,
        db=db,
        field_name="predecessor_task_id",
    )
    validate_task_reference(
        values.get("parent_task_id"),
        project_id=project_id,
        db=db,
        field_name="parent_task_id",
    )

    new_task = Task(project_id=project_id, **values)

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

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )
    recalculate_schedule(tasks)
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
        values = updated_task.model_dump(
            exclude={
                "predecessor",
                "predecessor_task_id",
                "dependency_type",
                "lag_days",
            },
            exclude_unset=True,
        )
        values.update(dependency_values(updated_task))

        predecessor_task_id = values.get(
            "predecessor_task_id",
            task.predecessor_task_id,
        )
        validate_dependency_assignment(
            task,
            predecessor_task_id,
            project_id=project_id,
            db=db,
        )

        if "parent_task_id" in values:
            validate_parent_assignment(
                task,
                values["parent_task_id"],
                project_id=project_id,
                db=db,
            )

        for field, value in values.items():
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

