from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task
from app.services.task_dependencies import task_dependencies


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

    parent_task = (
        db.query(Task)
        .filter(Task.id == parent_task_id, Task.project_id == project_id)
        .first()
    )
    if parent_task and task_dependencies(parent_task):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A task with a predecessor cannot become a summary task",
        )
    if parent_task and parent_task.is_milestone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Milestones cannot become summary tasks",
        )


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

    project_tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .all()
    )
    task_map = {item.id: item for item in project_tasks}
    pending = [predecessor_task_id]
    visited: set[int] = set()
    while pending:
        current_id = pending.pop()
        if current_id == task.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dependency assignment would create a cycle",
            )
        if current_id in visited:
            continue
        visited.add(current_id)
        current = task_map.get(current_id)
        if current is not None:
            pending.extend(
                dependency.predecessor_task_id
                for dependency in task_dependencies(current)
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
    if has_children:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Summary tasks cannot have predecessors",
        )


def validate_schedule_structure(tasks: list[Task]) -> None:
    """Reject dependency/hierarchy combinations with no stable schedule."""
    task_map = {task.id: task for task in tasks}
    children_by_parent: dict[int, list[int]] = {}
    for task in tasks:
        if task.parent_task_id in task_map:
            children_by_parent.setdefault(task.parent_task_id, []).append(
                task.id
            )

    prerequisites: dict[int, set[int]] = {task.id: set() for task in tasks}
    dependents: dict[int, list[int]] = {}
    for task in tasks:
        children = children_by_parent.get(task.id, [])
        if children:
            if task.is_milestone:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Milestones cannot be summary tasks",
                )
            if task.constraint_type != "ASAP" or task.constraint_date:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Summary task constraints must remain ASAP",
                )
            if task_dependencies(task):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Summary tasks cannot have predecessors",
                )
            prerequisites[task.id].update(children)
        else:
            predecessors = task_dependencies(task)
            predecessor_ids = [
                dependency.predecessor_task_id
                for dependency in predecessors
            ]
            if len(set(predecessor_ids)) != len(predecessor_ids):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="A predecessor can only be linked once",
                )
            for predecessor_id in predecessor_ids:
                if predecessor_id == task.id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="A task cannot depend on itself",
                    )
                if predecessor_id not in task_map:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            "Every predecessor must belong to this project"
                        ),
                    )
                prerequisites[task.id].add(predecessor_id)

        for prerequisite in prerequisites[task.id]:
            dependents.setdefault(prerequisite, []).append(task.id)

    ready = [
        task_id
        for task_id, required in prerequisites.items()
        if not required
    ]
    resolved = 0
    while ready:
        task_id = ready.pop()
        resolved += 1
        for dependent in dependents.get(task_id, []):
            prerequisites[dependent].discard(task_id)
            if not prerequisites[dependent]:
                ready.append(dependent)

    if resolved != len(tasks):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Task relationships create an unresolved scheduling cycle"
            ),
        )


def validate_hierarchy_order(tasks: list[Task], task_ids: list[int]) -> None:
    """Require a preorder traversal: parent first and each subtree contiguous."""
    task_map = {task.id: task for task in tasks}
    open_path: list[int] = []

    for task_id in task_ids:
        parent_id = task_map[task_id].parent_task_id
        if parent_id is None:
            open_path = [task_id]
            continue

        if parent_id not in open_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Task order must keep each parent before a contiguous "
                    "subtree"
                ),
            )

        parent_position = open_path.index(parent_id)
        open_path = open_path[: parent_position + 1]
        open_path.append(task_id)
