from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.models.task import Task, TaskDependency
from app.models.resource_planning import TaskResourceAssignment
from app.models.project import Project
from app.core.security import get_current_user
from app.domain.scheduling import is_workday
from app.schemas.common import MessageResponse
from app.schemas.task import (
    TaskCreate,
    TaskDependencyInput,
    TaskListResponse,
    TaskProgressUpdate,
    TaskReorderRequest,
    TaskUpdate,
    parse_predecessor_reference,
)
from app.services.task_scheduling import (
    lock_project_schedule,
    recalculate_schedule,
    task_list_payload,
)
from app.services.task_progress import update_task_progress
from app.services.task_dependencies import (
    dependency_inputs_from_task,
    replace_task_dependencies,
    sync_legacy_dependency_projection,
)
from app.services.task_validation import (
    validate_dependency_assignment,
    validate_hierarchy_order,
    validate_parent_assignment,
    validate_schedule_structure,
    validate_task_reference,
)
from app.services.project_schedule_settings import get_project_schedule_dates

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


def task_list_response(tasks: list[Task], *, data_date) -> dict:
    return task_list_payload(tasks, data_date=data_date)


def dependency_values(
    payload: TaskCreate | TaskUpdate,
    current_task: Task | None = None,
) -> list[TaskDependencyInput] | None:
    if "dependencies" in payload.model_fields_set:
        return list(payload.dependencies or [])

    if "predecessor" in payload.model_fields_set:
        predecessor_task_id, dependency_type, lag_days = (
            parse_predecessor_reference(payload.predecessor)
        )
        return (
            [
                TaskDependencyInput(
                    predecessor_task_id=predecessor_task_id,
                    dependency_type=dependency_type,
                    lag_days=lag_days,
                )
            ]
            if predecessor_task_id is not None
            else []
        )

    legacy_fields = {
        "predecessor_task_id",
        "dependency_type",
        "lag_days",
    }
    if not payload.model_fields_set.intersection(legacy_fields):
        return [] if isinstance(payload, TaskCreate) else None

    current = (
        dependency_inputs_from_task(current_task)
        if current_task is not None
        else []
    )
    primary = current[0] if current else None
    predecessor_task_id = (
        payload.predecessor_task_id
        if "predecessor_task_id" in payload.model_fields_set
        else primary.predecessor_task_id
        if primary
        else None
    )
    if predecessor_task_id is None:
        return []
    return [
        TaskDependencyInput(
            predecessor_task_id=predecessor_task_id,
            dependency_type=(
                payload.dependency_type
                if "dependency_type" in payload.model_fields_set
                else primary.dependency_type
                if primary
                else "FS"
            ),
            lag_days=(
                payload.lag_days
                if "lag_days" in payload.model_fields_set
                else primary.lag_days
                if primary
                else 0
            ),
        )
    ]


def validate_planning_values(
    *,
    is_milestone: bool,
    duration: int,
    constraint_type: str,
    constraint_date: str | None,
    progress_status: str = "not_started",
) -> None:
    if is_milestone and duration != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Milestones must have zero duration",
        )
    if not is_milestone and duration < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Non-milestone tasks require a duration",
        )
    if is_milestone and progress_status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="In Progress tasks cannot be milestones",
        )
    if constraint_type in ("ASAP", "ALAP"):
        if constraint_date is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{constraint_type} cannot have a constraint date",
            )
        return
    if constraint_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{constraint_type} requires a constraint date",
        )
    parsed_constraint = date.fromisoformat(constraint_date)
    if not is_workday(parsed_constraint):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Constraint dates must be project workdays",
        )


def recalculate_and_commit(
    db: Session,
    project_id: int,
    tasks: list[Task],
) -> date:
    try:
        project_start, data_date = get_project_schedule_dates(db, project_id)
        validate_schedule_structure(tasks)
        recalculate_schedule(
            tasks,
            project_start=project_start,
            data_date=data_date,
        )
        db.commit()
        return data_date
    except Exception:
        db.rollback()
        raise


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    _, data_date = get_project_schedule_dates(db, project_id)
    return task_list_response(
        ordered_project_tasks(db, project_id),
        data_date=data_date,
    )


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
    lock_project_schedule(db, project_id)
    values = task.model_dump(
        exclude={
            "predecessor",
            "predecessor_task_id",
            "dependency_type",
            "lag_days",
            "dependencies",
        }
    )
    dependencies = dependency_values(task) or []

    validate_planning_values(
        is_milestone=values["is_milestone"],
        duration=values["duration"],
        constraint_type=values["constraint_type"],
        constraint_date=values["constraint_date"],
    )
    validate_task_reference(
        values.get("parent_task_id"),
        project_id=project_id,
        db=db,
        field_name="parent_task_id",
    )

    new_task = Task(
        project_id=project_id,
        remaining_duration=(0 if values["is_milestone"] else values["duration"]),
        **values,
    )
    if new_task.parent_task_id is not None:
        validate_parent_assignment(
            new_task,
            new_task.parent_task_id,
            project_id=project_id,
            db=db,
        )

    db.add(new_task)
    db.flush()
    replace_task_dependencies(
        db,
        task=new_task,
        project_id=project_id,
        dependencies=dependencies,
    )
    db.flush()
    tasks = ordered_project_tasks(db, project_id)
    data_date = recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks, data_date=data_date)

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
    lock_project_schedule(db, project_id)
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
    lock_project_schedule(db, project_id)
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
            "dependencies",
        },
        exclude_unset=True,
    )
    dependencies = dependency_values(updated_task, task)

    if (
        values.get("constraint_type") in ("ASAP", "ALAP")
        and "constraint_date" not in values
    ):
        values["constraint_date"] = None
    next_is_milestone = values.get("is_milestone", task.is_milestone)
    next_duration = values.get("duration", task.duration)
    next_constraint_type = values.get(
        "constraint_type",
        task.constraint_type,
    )
    next_constraint_date = values.get(
        "constraint_date",
        task.constraint_date,
    )
    validate_planning_values(
        is_milestone=next_is_milestone,
        duration=next_duration,
        constraint_type=next_constraint_type,
        constraint_date=next_constraint_date,
        progress_status=task.progress_status,
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
    if task.progress_status == "not_started" and (
        "duration" in values or "is_milestone" in values
    ):
        task.remaining_duration = 0 if task.is_milestone else task.duration
    if dependencies is not None:
        replace_task_dependencies(
            db,
            task=task,
            project_id=project_id,
            dependencies=dependencies,
        )
        db.flush()

    tasks = ordered_project_tasks(db, project_id)
    if "parent_task_id" in values:
        validate_hierarchy_order(tasks, [item.id for item in tasks])
    data_date = recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks, data_date=data_date)


@router.put(
    "/projects/{project_id}/tasks/{task_id}/progress",
    response_model=TaskListResponse,
)
def update_project_task_progress(
    project_id: int,
    task_id: PositiveId,
    payload: TaskProgressUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return update_task_progress(
        db,
        project_id=project_id,
        task_id=task_id,
        payload=payload,
        updated_by=current_user["id"],
    )


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
    lock_project_schedule(db, project_id)
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

    affected_dependencies = (
        db.query(TaskDependency)
        .filter(
            TaskDependency.project_id == project_id,
            TaskDependency.predecessor_task_id == task.id,
        )
        .all()
    )
    affected_task_ids = {
        dependency.task_id for dependency in affected_dependencies
    }
    affected_tasks = {
        dependent.id: dependent
        for dependent in db.query(Task)
        .filter(Task.id.in_(affected_task_ids))
        .all()
    }
    for dependency in affected_dependencies:
        dependent = affected_tasks[dependency.task_id]
        dependent.dependencies.remove(dependency)
    for dependent in affected_tasks.values():
        sync_legacy_dependency_projection(
            dependent,
            list(dependent.dependencies),
        )

    db.query(TaskResourceAssignment).filter(
        TaskResourceAssignment.project_id == project_id,
        TaskResourceAssignment.task_id == task.id,
    ).delete(synchronize_session=False)
    db.delete(task)
    db.flush()
    tasks = ordered_project_tasks(db, project_id)
    data_date = recalculate_and_commit(db, project_id, tasks)

    return task_list_response(tasks, data_date=data_date)

