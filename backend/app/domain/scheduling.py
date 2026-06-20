from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal


DependencyType = Literal["FS", "SS"]


@dataclass(frozen=True)
class ScheduleTask:
    id: int | None
    name: str
    duration: int
    predecessor_task_id: int | None = None
    dependency_type: DependencyType = "FS"
    lag_days: int = 0
    parent_task_id: int | None = None
    manual_start_date: str | None = None


@dataclass(frozen=True)
class ScheduledTask:
    id: int | None
    name: str
    duration: int
    predecessor_task_id: int | None
    dependency_type: DependencyType
    lag_days: int
    parent_task_id: int | None
    manual_start_date: str | None
    start_date: str | None
    end_date: str | None


def is_workday(value: date) -> bool:
    return value.weekday() < 5


def next_workday(value: date) -> date:
    current = value

    while not is_workday(current):
        current += timedelta(days=1)

    return current


def add_workdays(start_date: date, duration: int) -> date:
    if duration < 1:
        raise ValueError("Task duration must be at least one workday")

    current = next_workday(start_date)
    days_counted = 1

    while days_counted < duration:
        current += timedelta(days=1)

        if is_workday(current):
            days_counted += 1

    return current


def calculate_schedule(
    tasks: list[ScheduleTask],
    *,
    project_start: date,
) -> list[ScheduledTask]:
    scheduled = [
        ScheduledTask(
            id=task.id,
            name=task.name,
            duration=task.duration,
            predecessor_task_id=task.predecessor_task_id,
            dependency_type=task.dependency_type,
            lag_days=task.lag_days,
            parent_task_id=task.parent_task_id,
            manual_start_date=task.manual_start_date,
            start_date=None,
            end_date=None,
        )
        for task in tasks
    ]

    for _ in range(len(scheduled)):
        changed = False

        for index, task in enumerate(scheduled):
            if task.start_date and task.end_date:
                continue

            start_date = _resolve_start_date(
                task,
                {candidate.id: candidate for candidate in scheduled},
                project_start,
            )

            if start_date is None:
                continue

            start_date = next_workday(start_date)
            end_date = add_workdays(start_date, task.duration)
            scheduled[index] = replace(
                task,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            changed = True

        if not changed:
            break

    return rollup_parent_tasks(scheduled)


def _resolve_start_date(
    task: ScheduledTask,
    task_map: dict[int | None, ScheduledTask],
    project_start: date,
) -> date | None:
    if task.predecessor_task_id is None:
        return (
            date.fromisoformat(task.manual_start_date)
            if task.manual_start_date
            else project_start
        )

    predecessor_task = task_map.get(task.predecessor_task_id)
    if predecessor_task is None:
        return None

    if task.dependency_type == "SS":
        if predecessor_task.start_date is None:
            return None

        return date.fromisoformat(predecessor_task.start_date) + timedelta(
            days=task.lag_days
        )

    if predecessor_task.end_date is None:
        return None

    return date.fromisoformat(predecessor_task.end_date) + timedelta(
        days=1 + task.lag_days
    )


def rollup_parent_tasks(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    rolled_up = list(tasks)

    task_map = {task.id: task for task in rolled_up}
    depths = {
        task.id: _hierarchy_depth(task, task_map)
        for task in rolled_up
    }

    ordered_indices = sorted(
        range(len(rolled_up)),
        key=lambda index: depths[rolled_up[index].id],
        reverse=True,
    )

    for index in ordered_indices:
        task = rolled_up[index]
        children = [
            candidate
            for candidate in rolled_up
            if candidate.parent_task_id == task.id
        ]

        scheduled_children = [
            child
            for child in children
            if child.start_date is not None and child.end_date is not None
        ]

        if not scheduled_children:
            continue

        rolled_up[index] = replace(
            task,
            start_date=min(child.start_date for child in scheduled_children),
            end_date=max(child.end_date for child in scheduled_children),
            duration=len(scheduled_children),
        )

    return rolled_up


def _hierarchy_depth(
    task: ScheduledTask,
    task_map: dict[int | None, ScheduledTask],
) -> int:
    depth = 0
    parent_id = task.parent_task_id
    visited: set[int] = set()

    while parent_id is not None and parent_id not in visited:
        visited.add(parent_id)
        parent = task_map.get(parent_id)

        if parent is None:
            break

        depth += 1
        parent_id = parent.parent_task_id

    return depth
