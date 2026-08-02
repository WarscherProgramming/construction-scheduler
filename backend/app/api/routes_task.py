from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
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
from app.services.task_scheduling import (
    annotate_critical_path,
    recalculate_schedule,
)
from app.services.task_validation import (
    validate_dependency_assignment,
    validate_hierarchy_order,
    validate_parent_assignment,
    validate_schedule_structure,
    validate_task_reference,
)
from app.services.project_schedule_settings import get_project_schedule_start

__all__ = [
    "router",
    "validate_dependency_assignment",
    "validate_hierarchy_order",
    "validate_parent_assignment",
    "validate_schedule_structure",
    "validate_task_reference",
]

router = APIRouter()


def ordered_project_tasks(db: Session, project_id: int) -> list[Task]:
    """The project's tasks in display order — the canonical task query."""
    return (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.order_index, Task.id)
        .all()
    )


def task_list_response(tasks: list[Task]) -> dict:
    """Annotate derived critical-path metadata and shape the response."""
    annotate_critical_path(tasks)
    return {"tasks": tasks}


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

    values = {
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
    if (
        isinstance(payload, TaskCreate)
        and values.get("predecessor_task_id") is None
    ) or (
        "predecessor_task_id" in values
        and values["predecessor_task_id"] is None
    ):
        values.update(
            predecessor_task_id=None,
            dependency_type="FS",
            lag_days=0,
        )
    return values


def recalculate_and_commit(
    db: Session,
    project_id: int,
    tasks: list[Task],
) -> None:
    try:
        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=get_project_schedule_start(db, project_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return task_list_response(ordered_project_tasks(db, project_id))


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
    if new_task.parent_task_id is not None:
        validate_parent_assignment(
            new_task,
            new_task.parent_task_id,
            project_id=project_id,
            db=db,
        )

    db.add(new_task)
    db.flush()
    tasks = ordered_project_tasks(db, project_id)
    recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks)

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
    if len(set(task_ids)) != len(task_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="task_ids must be unique",
        )

    tasks_to_reorder = ordered_project_tasks(db, project_id)
    if {task.id for task in tasks_to_reorder} != set(task_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task_map = {task.id: task for task in tasks_to_reorder}
    validate_hierarchy_order(tasks_to_reorder, task_ids)
    for index, task_id in enumerate(task_ids, start=1):
        task_map[task_id].order_index = index

    tasks = ordered_project_tasks(db, project_id)
    recalculate_and_commit(db, project_id, tasks)

    return {"message": "Tasks reordered"}

@router.put(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskListResponse,
)
def update_task(
    project_id: int,
    task_id: PositiveId,
    updated_task: TaskUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

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

    tasks = ordered_project_tasks(db, project_id)
    if "parent_task_id" in values:
        validate_hierarchy_order(tasks, [item.id for item in tasks])
    recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks)


@router.delete(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskListResponse,
)
def delete_task(
    project_id: int,
    task_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    db.delete(task)
    db.flush()
    tasks = ordered_project_tasks(db, project_id)
    recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks)

