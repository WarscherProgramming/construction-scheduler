from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task, TaskDependency
from app.schemas.task import DependencyType, TaskDependencyInput


@dataclass(frozen=True)
class LegacyTaskDependency:
    id: int = 0
    predecessor_task_id: int = 0
    dependency_type: DependencyType = "FS"
    lag_days: int = 0


def task_dependencies(task: Task) -> list[TaskDependency | LegacyTaskDependency]:
    rows = list(getattr(task, "dependencies", ()) or ())
    if rows or task.predecessor_task_id is None:
        return rows
    return [
        LegacyTaskDependency(
            predecessor_task_id=task.predecessor_task_id,
            dependency_type=task.dependency_type,
            lag_days=task.lag_days,
        )
    ]


def dependency_inputs_from_task(task: Task) -> list[TaskDependencyInput]:
    return [
        TaskDependencyInput(
            predecessor_task_id=row.predecessor_task_id,
            dependency_type=row.dependency_type,
            lag_days=row.lag_days,
        )
        for row in task_dependencies(task)
    ]


def sync_legacy_dependency_projection(
    task: Task,
    dependencies: list[TaskDependency | LegacyTaskDependency],
) -> None:
    primary = dependencies[0] if dependencies else None
    task.predecessor_task_id = (
        primary.predecessor_task_id if primary else None
    )
    task.dependency_type = primary.dependency_type if primary else "FS"
    task.lag_days = primary.lag_days if primary else 0


def replace_task_dependencies(
    db: Session,
    *,
    task: Task,
    project_id: int,
    dependencies: list[TaskDependencyInput],
) -> None:
    predecessor_ids = [row.predecessor_task_id for row in dependencies]
    if len(set(predecessor_ids)) != len(predecessor_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A predecessor can only be linked to a task once",
        )
    if task.id in predecessor_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A task cannot depend on itself",
        )

    if predecessor_ids:
        valid_ids = {
            row[0]
            for row in db.query(Task.id)
            .filter(
                Task.project_id == project_id,
                Task.id.in_(predecessor_ids),
            )
            .all()
        }
        if valid_ids != set(predecessor_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Every predecessor must reference a task in this project",
            )

    has_children = (
        db.query(Task.id)
        .filter(
            Task.project_id == project_id,
            Task.parent_task_id == task.id,
        )
        .first()
        is not None
    )
    if has_children and dependencies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Summary tasks cannot have predecessors",
        )

    task.dependencies.clear()
    db.flush()
    for row in dependencies:
        task.dependencies.append(
            TaskDependency(
                project_id=project_id,
                predecessor_task_id=row.predecessor_task_id,
                dependency_type=row.dependency_type,
                lag_days=row.lag_days,
            )
        )

    sync_legacy_dependency_projection(task, list(task.dependencies))
