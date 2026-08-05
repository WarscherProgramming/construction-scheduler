from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import lru_cache
import heapq
from typing import Literal


DependencyType = Literal["FS", "SS", "FF", "SF"]
ProgressStatus = Literal["not_started", "in_progress", "completed"]
ConstraintType = Literal[
    "ASAP",
    "ALAP",
    "SNET",
    "SNLT",
    "FNET",
    "FNLT",
    "MS",
    "MF",
]


@dataclass(frozen=True)
class ScheduleDependency:
    predecessor_task_id: int
    dependency_type: DependencyType = "FS"
    lag_days: int = 0


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
    progress_status: ProgressStatus = "not_started"
    percent_complete: int = 0
    actual_start_date: str | None = None
    actual_finish_date: str | None = None
    remaining_duration: int | None = None
    dependencies: tuple[ScheduleDependency, ...] = ()
    is_milestone: bool = False
    constraint_type: ConstraintType = "ASAP"
    constraint_date: str | None = None


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
    progress_status: ProgressStatus = "not_started"
    percent_complete: int = 0
    actual_start_date: str | None = None
    actual_finish_date: str | None = None
    remaining_duration: int | None = None
    dependencies: tuple[ScheduleDependency, ...] = ()
    is_milestone: bool = False
    constraint_type: ConstraintType = "ASAP"
    constraint_date: str | None = None
    constraint_violated: bool = False
    constraint_violation_reason: str | None = None
    out_of_sequence: bool = False
    out_of_sequence_reason: str | None = None
    calculation_start_date: str | None = None
    progress_weight: int = 0
    progress_weighted_value: int = 0
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


def _finish_from_start(start: date, duration: int) -> date:
    return next_workday(start) if duration == 0 else add_workdays(start, duration)


def _start_from_finish(finish: date, duration: int) -> date:
    return (
        previous_workday(finish)
        if duration == 0
        else subtract_workdays(finish, duration)
    )


def _signed_workdays_between(start: date, end: date) -> int:
    if end >= start:
        return workdays_between(start, end)
    return -workdays_between(end, start)


def _task_dependencies(
    task: ScheduleTask | ScheduledTask,
) -> tuple[ScheduleDependency, ...]:
    if task.dependencies:
        return task.dependencies
    if task.predecessor_task_id is None:
        return ()
    return (
        ScheduleDependency(
            predecessor_task_id=task.predecessor_task_id,
            dependency_type=task.dependency_type,
            lag_days=task.lag_days,
        ),
    )


def calculate_schedule(
    tasks: list[ScheduleTask],
    *,
    project_start: date,
    data_date: date | None = None,
) -> list[ScheduledTask]:
    status_date = data_date or project_start
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
            progress_status=task.progress_status,
            percent_complete=task.percent_complete,
            actual_start_date=task.actual_start_date,
            actual_finish_date=task.actual_finish_date,
            remaining_duration=(
                task.remaining_duration
                if task.remaining_duration is not None
                else task.duration
            ),
            dependencies=_task_dependencies(task),
            is_milestone=task.is_milestone,
            constraint_type=task.constraint_type,
            constraint_date=task.constraint_date,
        )
        for task in tasks
    ]

    id_to_index: dict[int, int] = {}
    for index, task in enumerate(scheduled):
        if task.id is None:
            continue
        if task.id in id_to_index:
            raise ValueError("Task IDs must be unique")
        id_to_index[task.id] = index

    children_by_parent: dict[int, list[int]] = {}
    for index, task in enumerate(scheduled):
        if task.parent_task_id in id_to_index:
            children_by_parent.setdefault(task.parent_task_id, []).append(index)

    prerequisites: list[set[int]] = [set() for _ in scheduled]
    dependents: dict[int, list[int]] = {}
    for index, task in enumerate(scheduled):
        child_indices = children_by_parent.get(task.id, [])
        if child_indices:
            if _task_dependencies(task):
                raise ValueError("Summary tasks cannot have predecessors")
            prerequisites[index].update(child_indices)
        else:
            for dependency in _task_dependencies(task):
                if dependency.predecessor_task_id in id_to_index:
                    prerequisites[index].add(
                        id_to_index[dependency.predecessor_task_id]
                    )

        for prerequisite in prerequisites[index]:
            dependents.setdefault(prerequisite, []).append(index)

    indegree = [len(items) for items in prerequisites]
    ready = [index for index, count in enumerate(indegree) if count == 0]
    heapq.heapify(ready)
    task_map = {
        task.id: task for task in scheduled if task.id is not None
    }

    # Every node is finalized at most once. Nodes left outside the topological
    # order are part of a dependency/hierarchy cycle and remain unscheduled.
    while ready:
        index = heapq.heappop(ready)
        task = scheduled[index]
        child_indices = children_by_parent.get(task.id, [])

        if child_indices:
            children = [scheduled[child_index] for child_index in child_indices]
            if all(child.start_date and child.end_date for child in children):
                task = replace(
                    task,
                    start_date=min(child.start_date for child in children),
                    end_date=max(child.end_date for child in children),
                    # Retained display contract: direct scheduled-child count.
                    duration=len(children),
                )
                scheduled[index] = task
        else:
            task = _schedule_leaf_task(
                task,
                task_map,
                project_start=project_start,
                data_date=status_date,
            )
            scheduled[index] = task

        if task.id is not None:
            task_map[task.id] = task

        for dependent in dependents.get(index, []):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    return annotate_schedule(scheduled)


def _schedule_leaf_task(
    task: ScheduledTask,
    task_map: dict[int | None, ScheduledTask],
    *,
    project_start: date,
    data_date: date,
) -> ScheduledTask:
    if task.progress_status == "completed":
        return replace(
            task,
            start_date=task.actual_start_date,
            end_date=task.actual_finish_date,
            calculation_start_date=None,
        )

    duration = (
        task.remaining_duration
        if task.remaining_duration is not None
        else task.duration
    )
    data_boundary = next_workday(data_date)
    earliest_start = _resolve_earliest_start(
        task,
        task_map,
        project_start=project_start,
        duration=duration,
    )
    if earliest_start is None:
        return replace(
            task,
            start_date=(
                task.actual_start_date
                if task.progress_status == "in_progress"
                else None
            ),
            end_date=None,
            calculation_start_date=None,
        )

    if task.progress_status == "in_progress":
        remaining_start = max(data_boundary, earliest_start)
        return replace(
            task,
            start_date=task.actual_start_date,
            end_date=_finish_from_start(
                remaining_start,
                duration,
            ).isoformat(),
            calculation_start_date=remaining_start.isoformat(),
        )

    normal_start = max(earliest_start, data_boundary)
    start_date = normal_start
    if task.constraint_type == "MS" and task.constraint_date:
        start_date = date.fromisoformat(task.constraint_date)
    elif task.constraint_type == "MF" and task.constraint_date:
        start_date = _start_from_finish(
            date.fromisoformat(task.constraint_date),
            duration,
        )

    constraint_violated = start_date < normal_start
    violation_reason = (
        "Mandatory constraint conflicts with dependency, manual-date, or "
        "Data Date logic."
        if constraint_violated
        else None
    )
    return replace(
        task,
        start_date=start_date.isoformat(),
        end_date=_finish_from_start(start_date, duration).isoformat(),
        calculation_start_date=start_date.isoformat(),
        constraint_violated=constraint_violated,
        constraint_violation_reason=violation_reason,
    )


def _resolve_earliest_start(
    task: ScheduledTask,
    task_map: dict[int | None, ScheduledTask],
    *,
    project_start: date,
    duration: int,
) -> date | None:
    boundaries = [project_start]
    if task.manual_start_date:
        boundaries.append(date.fromisoformat(task.manual_start_date))

    for dependency in _task_dependencies(task):
        predecessor = task_map.get(dependency.predecessor_task_id)
        if predecessor is None:
            return None
        boundary = _dependency_start_boundary(
            dependency,
            predecessor,
            duration=duration,
        )
        if boundary is None:
            return None
        boundaries.append(boundary)

    if task.constraint_type == "SNET" and task.constraint_date:
        boundaries.append(date.fromisoformat(task.constraint_date))
    if task.constraint_type == "FNET" and task.constraint_date:
        boundaries.append(
            _start_from_finish(
                date.fromisoformat(task.constraint_date),
                duration,
            )
        )
    return max(next_workday(boundary) for boundary in boundaries)


def _dependency_start_boundary(
    dependency: ScheduleDependency,
    predecessor: ScheduledTask,
    *,
    duration: int,
) -> date | None:
    if dependency.dependency_type in ("SS", "SF"):
        if predecessor.start_date is None:
            return None
        predecessor_anchor = date.fromisoformat(predecessor.start_date)
    else:
        if predecessor.end_date is None:
            return None
        predecessor_anchor = date.fromisoformat(predecessor.end_date)

    extra_days = (
        1 + dependency.lag_days
        if dependency.dependency_type == "FS"
        else dependency.lag_days
    )
    boundary = next_workday(predecessor_anchor + timedelta(days=extra_days))
    if dependency.dependency_type in ("FF", "SF"):
        return _start_from_finish(boundary, duration)
    return boundary


def annotate_schedule(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    late_scheduled = _apply_alap(tasks)
    progress = _rollup_progress(late_scheduled)
    constrained = _apply_constraint_violations(progress)
    sequenced = _apply_out_of_sequence(constrained)
    return apply_critical_path(sequenced)


def _rollup_progress(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    rolled_up = [
        replace(
            task,
            remaining_duration=(
                task.remaining_duration
                if task.remaining_duration is not None
                else task.duration
            ),
            progress_weight=task.duration,
            progress_weighted_value=task.duration * task.percent_complete,
        )
        for task in tasks
    ]
    children_by_parent: dict[int | None, list[ScheduledTask]] = {}
    for task in rolled_up:
        children_by_parent.setdefault(task.parent_task_id, []).append(task)
    depths = _hierarchy_depths(rolled_up)

    for index in sorted(
        range(len(rolled_up)),
        key=lambda item: depths[rolled_up[item].id],
        reverse=True,
    ):
        task = rolled_up[index]
        children = children_by_parent.get(task.id, [])
        if not children:
            continue

        weight = sum(child.progress_weight for child in children)
        weighted_value = sum(
            child.progress_weighted_value for child in children
        )
        all_completed = all(
            child.progress_status == "completed" for child in children
        )
        percent_complete = (
            (weighted_value + weight // 2) // weight
            if weight
            else 100
            if all_completed
            else 0
        )
        if all_completed:
            progress_status: ProgressStatus = "completed"
        elif any(
            child.progress_status != "not_started" for child in children
        ):
            progress_status = "in_progress"
        else:
            progress_status = "not_started"

        actual_starts = [
            child.actual_start_date
            for child in children
            if child.actual_start_date is not None
        ]
        actual_finishes = [
            child.actual_finish_date
            for child in children
            if child.actual_finish_date is not None
        ]
        rolled_up[index] = replace(
            task,
            progress_status=progress_status,
            percent_complete=percent_complete,
            actual_start_date=min(actual_starts) if actual_starts else None,
            actual_finish_date=(
                max(actual_finishes)
                if progress_status == "completed" and actual_finishes
                else None
            ),
            remaining_duration=None,
            progress_weight=weight,
            progress_weighted_value=weighted_value,
        )
        children_by_parent[task.parent_task_id] = [
            rolled_up[index] if child.id == task.id else child
            for child in children_by_parent.get(task.parent_task_id, [])
        ]

    return rolled_up


def _apply_alap(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    late_starts = _compute_late_starts(tasks)
    if not late_starts:
        return tasks

    parent_ids = {
        task.parent_task_id
        for task in tasks
        if task.parent_task_id is not None
    }
    adjusted: list[ScheduledTask] = []
    for task in tasks:
        late_start = late_starts.get(task.id)
        if (
            task.id in parent_ids
            or task.progress_status != "not_started"
            or task.constraint_type != "ALAP"
            or late_start is None
        ):
            adjusted.append(task)
            continue
        duration = _critical_duration(task)
        adjusted.append(
            replace(
                task,
                start_date=late_start.isoformat(),
                end_date=_finish_from_start(
                    late_start,
                    duration,
                ).isoformat(),
                calculation_start_date=late_start.isoformat(),
            )
        )
    return rollup_parent_tasks(adjusted)


def _apply_constraint_violations(
    tasks: list[ScheduledTask],
) -> list[ScheduledTask]:
    annotated: list[ScheduledTask] = []
    labels = {
        "SNET": "Start No Earlier Than",
        "SNLT": "Start No Later Than",
        "FNET": "Finish No Earlier Than",
        "FNLT": "Finish No Later Than",
        "MS": "Mandatory Start",
        "MF": "Mandatory Finish",
    }
    for task in tasks:
        if (
            task.constraint_type in ("ASAP", "ALAP")
            or task.constraint_date is None
            or task.start_date is None
            or task.end_date is None
        ):
            annotated.append(task)
            continue

        target = date.fromisoformat(task.constraint_date)
        start = date.fromisoformat(task.start_date)
        finish = date.fromisoformat(task.end_date)
        violated = {
            "SNET": start < target,
            "SNLT": start > target,
            "FNET": finish < target,
            "FNLT": finish > target,
            "MS": start != target,
            "MF": finish != target,
        }[task.constraint_type]
        violated = violated or task.constraint_violated
        reason = task.constraint_violation_reason
        if violated and reason is None:
            reason = (
                f"{labels[task.constraint_type]} "
                f"{task.constraint_date} is not satisfied."
            )
        annotated.append(
            replace(
                task,
                constraint_violated=violated,
                constraint_violation_reason=reason if violated else None,
            )
        )
    return annotated


def _dependency_boundary(
    dependency: ScheduleDependency,
    predecessor: ScheduledTask,
) -> date | None:
    value = (
        predecessor.start_date
        if dependency.dependency_type in ("SS", "SF")
        else predecessor.end_date
    )
    if value is None:
        return None
    extra_days = (
        1 + dependency.lag_days
        if dependency.dependency_type == "FS"
        else dependency.lag_days
    )
    return next_workday(date.fromisoformat(value) + timedelta(days=extra_days))


def _apply_out_of_sequence(
    tasks: list[ScheduledTask],
) -> list[ScheduledTask]:
    annotated = list(tasks)
    task_map = {task.id: task for task in annotated}
    parent_ids = {
        task.parent_task_id
        for task in annotated
        if task.parent_task_id is not None
    }

    for index, task in enumerate(annotated):
        if (
            task.id in parent_ids
            or not _task_dependencies(task)
            or (
                task.actual_start_date is None
                and task.actual_finish_date is None
            )
        ):
            continue
        reasons: list[str] = []
        for dependency in _task_dependencies(task):
            predecessor = task_map.get(dependency.predecessor_task_id)
            if predecessor is None:
                reasons.append(
                    "Progress was recorded while predecessor "
                    f"{dependency.predecessor_task_id} was unavailable."
                )
                continue
            boundary = _dependency_boundary(dependency, predecessor)
            if boundary is None:
                reasons.append(
                    "Progress was recorded while predecessor "
                    f"{predecessor.id} was unscheduled."
                )
                continue
            actual_value = (
                task.actual_start_date
                if dependency.dependency_type in ("FS", "SS")
                else task.actual_finish_date
            )
            if actual_value is None:
                continue
            if date.fromisoformat(actual_value) < boundary:
                event = (
                    "Actual start"
                    if dependency.dependency_type in ("FS", "SS")
                    else "Actual finish"
                )
                reasons.append(
                    f"{event} {actual_value} is before the "
                    f"{dependency.dependency_type} predecessor boundary "
                    f"{boundary.isoformat()} from task {predecessor.id}."
                )
        if reasons:
            annotated[index] = replace(
                task,
                out_of_sequence=True,
                out_of_sequence_reason=" ".join(reasons),
            )

    children_by_parent: dict[int | None, list[ScheduledTask]] = {}
    for task in annotated:
        children_by_parent.setdefault(task.parent_task_id, []).append(task)
    depths = _hierarchy_depths(annotated)
    for index in sorted(
        range(len(annotated)),
        key=lambda item: depths[annotated[item].id],
        reverse=True,
    ):
        task = annotated[index]
        children = children_by_parent.get(task.id, [])
        flagged = [child for child in children if child.out_of_sequence]
        if not flagged:
            continue
        annotated[index] = replace(
            task,
            out_of_sequence=True,
            out_of_sequence_reason=(
                f"{len(flagged)} direct descendant task"
                f"{'s are' if len(flagged) != 1 else ' is'} out of sequence."
            ),
        )
        children_by_parent[task.parent_task_id] = [
            annotated[index] if child.id == task.id else child
            for child in children_by_parent.get(task.parent_task_id, [])
        ]

    return annotated


def _remaining_schedule_nodes(
    tasks: list[ScheduledTask],
) -> list[ScheduledTask]:
    parent_ids = {
        task.parent_task_id for task in tasks if task.parent_task_id is not None
    }
    return [
        task
        for task in tasks
        if task.id not in parent_ids
        and task.progress_status != "completed"
        and task.start_date
        and task.end_date
        and _critical_duration(task) >= 0
    ]


def _latest_predecessor_start(
    predecessor: ScheduledTask,
    successor: ScheduledTask,
    dependency: ScheduleDependency,
    successor_late_start: date,
) -> date:
    successor_late_finish = _finish_from_start(
        successor_late_start,
        _critical_duration(successor),
    )
    if dependency.dependency_type == "FS":
        latest_finish = previous_workday(
            successor_late_start
            - timedelta(days=1 + dependency.lag_days)
        )
        return _start_from_finish(
            latest_finish,
            _critical_duration(predecessor),
        )
    if dependency.dependency_type == "SS":
        return previous_workday(
            successor_late_start - timedelta(days=dependency.lag_days)
        )
    if dependency.dependency_type == "FF":
        latest_finish = previous_workday(
            successor_late_finish - timedelta(days=dependency.lag_days)
        )
        return _start_from_finish(
            latest_finish,
            _critical_duration(predecessor),
        )
    return previous_workday(
        successor_late_finish - timedelta(days=dependency.lag_days)
    )


def _compute_late_starts(
    tasks: list[ScheduledTask],
) -> dict[int | None, date]:
    nodes = _remaining_schedule_nodes(tasks)
    if not nodes:
        return {}

    node_map = {task.id: task for task in nodes}
    successors: dict[
        int | None,
        list[tuple[ScheduledTask, ScheduleDependency]],
    ] = {}
    indegree = {task.id: 0 for task in nodes}

    for task in nodes:
        for dependency in _task_dependencies(task):
            if dependency.predecessor_task_id in node_map:
                successors.setdefault(
                    dependency.predecessor_task_id,
                    [],
                ).append((task, dependency))
                indegree[task.id] += 1

    project_end = max(date.fromisoformat(task.end_date) for task in nodes)
    late_start: dict[int | None, date] = {}
    task_order = {task.id: index for index, task in enumerate(nodes)}
    ready = [
        (task_order[task.id], task.id)
        for task in nodes
        if indegree[task.id] == 0
    ]
    heapq.heapify(ready)
    topological_ids: list[int | None] = []

    while ready:
        _, task_id = heapq.heappop(ready)
        topological_ids.append(task_id)
        for successor, _ in successors.get(task_id, []):
            indegree[successor.id] -= 1
            if indegree[successor.id] == 0:
                heapq.heappush(
                    ready,
                    (task_order[successor.id], successor.id),
                )

    for task_id in reversed(topological_ids):
        task = node_map[task_id]
        following = successors.get(task.id, [])
        candidates = [
            _start_from_finish(project_end, _critical_duration(task))
        ]
        if task.constraint_date and task.constraint_type in ("SNLT", "MS"):
            candidates.append(date.fromisoformat(task.constraint_date))
        if task.constraint_date and task.constraint_type in ("FNLT", "MF"):
            candidates.append(
                _start_from_finish(
                    date.fromisoformat(task.constraint_date),
                    _critical_duration(task),
                )
            )

        for successor, dependency in following:
            successor_late_start = late_start[successor.id]
            candidates.append(
                _latest_predecessor_start(
                    task,
                    successor,
                    dependency,
                    successor_late_start,
                )
            )

        late_start[task.id] = min(candidates)

    return late_start


def compute_critical_path(
    tasks: list[ScheduledTask],
) -> dict[int | None, tuple[int | None, bool]]:
    """CPM backward pass over remaining scheduled leaf work."""
    nodes = _remaining_schedule_nodes(tasks)
    late_start = _compute_late_starts(tasks)

    results: dict[int | None, tuple[int | None, bool]] = {}

    for task in nodes:
        resolved_late_start = late_start.get(task.id)

        if resolved_late_start is None:
            results[task.id] = (None, False)
            continue

        early_start = date.fromisoformat(
            task.calculation_start_date or task.start_date
        )
        total_float = _signed_workdays_between(
            early_start,
            resolved_late_start,
        )
        results[task.id] = (total_float, total_float <= 0)

    return results


def apply_critical_path(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    results = compute_critical_path(tasks)

    annotated = [
        replace(
            task,
            total_float=results.get(
                task.id,
                (
                    0 if task.progress_status == "completed" else None,
                    False,
                ),
            )[0],
            is_critical=results.get(task.id, (None, False))[1],
        )
        for task in tasks
    ]

    # Summary tasks aggregate their children, deepest parents first so the
    # values bubble up through nested hierarchies.
    children_by_parent: dict[int | None, list[ScheduledTask]] = {}
    for task in annotated:
        children_by_parent.setdefault(task.parent_task_id, []).append(task)
    depths = _hierarchy_depths(annotated)
    ordered_indices = sorted(
        range(len(annotated)),
        key=lambda index: depths[annotated[index].id],
        reverse=True,
    )

    for index in ordered_indices:
        task = annotated[index]
        children = children_by_parent.get(task.id, [])

        if not children:
            continue

        child_floats = [
            child.total_float
            for child in children
            if child.progress_status != "completed"
            and child.total_float is not None
        ]
        annotated[index] = replace(
            task,
            is_critical=any(
                child.progress_status != "completed" and child.is_critical
                for child in children
            ),
            total_float=(
                min(child_floats)
                if child_floats
                else 0
                if task.progress_status == "completed"
                else None
            ),
        )
        children_by_parent[task.parent_task_id] = [
            annotated[index] if child.id == task.id else child
            for child in children_by_parent.get(task.parent_task_id, [])
        ]

    return annotated


def _critical_duration(task: ScheduledTask) -> int:
    return task.remaining_duration or task.duration


def rollup_parent_tasks(tasks: list[ScheduledTask]) -> list[ScheduledTask]:
    rolled_up = list(tasks)

    children_by_parent: dict[int | None, list[ScheduledTask]] = {}
    for task in rolled_up:
        children_by_parent.setdefault(task.parent_task_id, []).append(task)
    depths = _hierarchy_depths(rolled_up)

    ordered_indices = sorted(
        range(len(rolled_up)),
        key=lambda index: depths[rolled_up[index].id],
        reverse=True,
    )

    for index in ordered_indices:
        task = rolled_up[index]
        children = children_by_parent.get(task.id, [])

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
        children_by_parent[task.parent_task_id] = [
            rolled_up[index] if child.id == task.id else child
            for child in children_by_parent.get(task.parent_task_id, [])
        ]

    return rolled_up


def _hierarchy_depths(
    tasks: list[ScheduledTask],
) -> dict[int | None, int]:
    task_map = {task.id: task for task in tasks}
    depths: dict[int | None, int] = {}

    for task in tasks:
        if task.id in depths:
            continue

        trail: list[int | None] = []
        positions: dict[int | None, int] = {}
        current_id = task.id

        while (
            current_id in task_map
            and current_id not in depths
            and current_id not in positions
        ):
            positions[current_id] = len(trail)
            trail.append(current_id)
            current_id = task_map[current_id].parent_task_id

        if current_id in depths:
            depth = depths[current_id]
        elif current_id in positions:
            cycle_start = positions[current_id]
            for cycle_id in trail[cycle_start:]:
                depths[cycle_id] = 0
            trail = trail[:cycle_start]
            depth = 0
        else:
            depth = -1

        for task_id in reversed(trail):
            depth += 1
            depths[task_id] = depth

    return depths
