from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import lru_cache
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
    total_float: int | None = None
    is_critical: bool = False


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(holiday: date) -> date:
    # Federal observance: Saturday holidays shift to Friday, Sunday to Monday.
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


@lru_cache(maxsize=None)
def federal_holidays(year: int) -> frozenset[date]:
    """Observed US federal holidays for the given year."""
    fixed = [
        date(year, 1, 1),    # New Year's Day
        date(year, 6, 19),   # Juneteenth
        date(year, 7, 4),    # Independence Day
        date(year, 11, 11),  # Veterans Day
        date(year, 12, 25),  # Christmas Day
    ]
    floating = [
        _nth_weekday(year, 1, 0, 3),   # Birthday of Martin Luther King, Jr.
        _nth_weekday(year, 2, 0, 3),   # Washington's Birthday
        _last_weekday(year, 5, 0),     # Memorial Day
        _nth_weekday(year, 9, 0, 1),   # Labor Day
        _nth_weekday(year, 10, 0, 2),  # Columbus Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving Day
    ]

    return frozenset({_observed(holiday) for holiday in fixed} | set(floating))


def is_workday(value: date) -> bool:
    if value.weekday() >= 5:
        return False

    # A January 1 falling on Saturday is observed on December 31 of the
    # previous year, so late-December dates must also consult next year's set.
    return (
        value not in federal_holidays(value.year)
        and value not in federal_holidays(value.year + 1)
    )


def next_workday(value: date) -> date:
    current = value

    while not is_workday(current):
        current += timedelta(days=1)

    return current


def previous_workday(value: date) -> date:
    current = value

    while not is_workday(current):
        current -= timedelta(days=1)

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


def subtract_workdays(end_date: date, duration: int) -> date:
    """Latest start (inclusive) such that `duration` workdays end on `end_date`."""
    if duration < 1:
        raise ValueError("Task duration must be at least one workday")

    current = previous_workday(end_date)
    days_counted = 1

    while days_counted < duration:
        current -= timedelta(days=1)

        if is_workday(current):
            days_counted += 1

    return current


def workdays_between(start: date, end: date) -> int:
    """Workdays strictly after `start` up to and including `end`."""
    if end <= start:
        return 0

    count = 0
    current = start

    while current < end:
        current += timedelta(days=1)

        if is_workday(current):
            count += 1

    return count


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

    return apply_critical_path(rollup_parent_tasks(scheduled))


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


def compute_critical_path(
    tasks: list[ScheduledTask],
) -> dict[int | None, tuple[int | None, bool]]:
    """CPM backward pass over scheduled leaf tasks.

    Returns {task_id: (total_float_in_workdays, is_critical)}. Mirrors the
    forward pass exactly: FS/SS with calendar-day lag snapped to the workday
    calendar, so a computed late start of X guarantees the forward pass would
    still hit every successor's late start. Summary (parent) tasks are
    aggregated from their children by apply_critical_path.
    """
    parent_ids = {
        task.parent_task_id for task in tasks if task.parent_task_id is not None
    }
    nodes = [
        task
        for task in tasks
        if task.id not in parent_ids
        and task.start_date
        and task.end_date
        and task.duration >= 1
    ]

    if not nodes:
        return {}

    node_map = {task.id: task for task in nodes}
    successors: dict[int | None, list[ScheduledTask]] = {}

    for task in nodes:
        if task.predecessor_task_id in node_map:
            successors.setdefault(task.predecessor_task_id, []).append(task)

    project_end = max(date.fromisoformat(task.end_date) for task in nodes)
    late_start: dict[int | None, date] = {}

    for _ in range(len(nodes)):
        changed = False

        for task in nodes:
            if task.id in late_start:
                continue

            following = successors.get(task.id, [])

            if any(successor.id not in late_start for successor in following):
                continue

            # Every task is bounded by the project end; successor links can
            # only tighten that bound.
            candidates = [subtract_workdays(project_end, task.duration)]

            for successor in following:
                successor_late_start = late_start[successor.id]

                if successor.dependency_type == "SS":
                    candidates.append(
                        previous_workday(
                            successor_late_start
                            - timedelta(days=successor.lag_days)
                        )
                    )
                else:
                    latest_finish = previous_workday(
                        successor_late_start
                        - timedelta(days=1 + successor.lag_days)
                    )
                    candidates.append(
                        subtract_workdays(latest_finish, task.duration)
                    )

            late_start[task.id] = min(candidates)
            changed = True

        if not changed:
            break

    results: dict[int | None, tuple[int | None, bool]] = {}

    for task in nodes:
        resolved_late_start = late_start.get(task.id)

        if resolved_late_start is None:
            results[task.id] = (None, False)
            continue

        early_start = date.fromisoformat(task.start_date)
        total_float = workdays_between(early_start, resolved_late_start)
        results[task.id] = (total_float, total_float == 0)

    return results


def apply_critical_path(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    results = compute_critical_path(tasks)

    annotated = [
        replace(
            task,
            total_float=results.get(task.id, (None, False))[0],
            is_critical=results.get(task.id, (None, False))[1],
        )
        for task in tasks
    ]

    # Summary tasks aggregate their children, deepest parents first so the
    # values bubble up through nested hierarchies.
    task_map = {task.id: task for task in annotated}
    depths = {task.id: _hierarchy_depth(task, task_map) for task in annotated}
    ordered_indices = sorted(
        range(len(annotated)),
        key=lambda index: depths[annotated[index].id],
        reverse=True,
    )

    for index in ordered_indices:
        task = annotated[index]
        children = [
            candidate
            for candidate in annotated
            if candidate.parent_task_id == task.id
        ]

        if not children:
            continue

        child_floats = [
            child.total_float
            for child in children
            if child.total_float is not None
        ]
        annotated[index] = replace(
            task,
            is_critical=any(child.is_critical for child in children),
            total_float=min(child_floats) if child_floats else None,
        )
        task_map[task.id] = annotated[index]

    return annotated


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
