from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task


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
