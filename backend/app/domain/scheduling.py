from dataclasses import dataclass, replace
from datetime import date, timedelta
import re
from typing import Literal


DependencyType = Literal["FS", "SS"]


@dataclass(frozen=True)
class ScheduleTask:
    id: int | None
    name: str
    duration: int
    predecessor: str | None = None
    manual_start_date: str | None = None


@dataclass(frozen=True)
class ScheduledTask:
    id: int | None
    name: str
    duration: int
    predecessor: str | None
    manual_start_date: str | None
    start_date: str | None
    end_date: str | None


@dataclass(frozen=True)
class ParsedPredecessor:
    task_number: int
    relationship: DependencyType
    lag_days: int


PREDECESSOR_PATTERN = re.compile(r"^(\d+)(SS)?(?:\+(\d+)D?)?$")


def parse_predecessor(value: str | None) -> ParsedPredecessor | None:
    if not value:
        return None

    normalized = str(value).replace(" ", "").upper()
    match = PREDECESSOR_PATTERN.fullmatch(normalized)

    if match is None:
        return None

    return ParsedPredecessor(
        task_number=int(match.group(1)),
        relationship="SS" if match.group(2) else "FS",
        lag_days=int(match.group(3) or 0),
    )


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
            predecessor=task.predecessor,
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

            predecessor = parse_predecessor(task.predecessor)
            start_date = _resolve_start_date(
                task,
                predecessor,
                scheduled,
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
    predecessor: ParsedPredecessor | None,
    scheduled: list[ScheduledTask],
    project_start: date,
) -> date | None:
    if predecessor is None:
        return (
            date.fromisoformat(task.manual_start_date)
            if task.manual_start_date
            else project_start
        )

    predecessor_index = predecessor.task_number - 1
    if predecessor_index < 0 or predecessor_index >= len(scheduled):
        return None

    predecessor_task = scheduled[predecessor_index]

    if predecessor.relationship == "SS":
        if predecessor_task.start_date is None:
            return None

        return date.fromisoformat(predecessor_task.start_date) + timedelta(
            days=predecessor.lag_days
        )

    if predecessor_task.end_date is None:
        return None

    return date.fromisoformat(predecessor_task.end_date) + timedelta(
        days=1 + predecessor.lag_days
    )


def rollup_parent_tasks(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    rolled_up = list(tasks)

    for index, task in enumerate(rolled_up):
        current_level = get_indent_level(task.name)
        children: list[ScheduledTask] = []

        for candidate in rolled_up[index + 1 :]:
            candidate_level = get_indent_level(candidate.name)

            if candidate_level <= current_level:
                break

            if candidate_level == current_level + 1:
                children.append(candidate)

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


def get_indent_level(name: str) -> int:
    leading_spaces = len(name) - len(name.lstrip(" "))
    return leading_spaces // 4
