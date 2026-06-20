"""Use stable task IDs for dependencies and hierarchy.

Revision ID: 7c2f4a9d1e30
Revises: 4b7d9c2a6f10
Create Date: 2026-06-20
"""

from collections import defaultdict
from collections.abc import Sequence
import re

from alembic import op
import sqlalchemy as sa


revision: str = "7c2f4a9d1e30"
down_revision: str | Sequence[str] | None = "4b7d9c2a6f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PREDECESSOR_PATTERN = re.compile(r"^(\d+)(SS)?(?:\+(\d+)D?)?$")


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("predecessor_task_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "dependency_type",
            sa.String(length=2),
            server_default="FS",
            nullable=False,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "lag_days",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.add_column(
        "schedule_template_tasks",
        sa.Column(
            "predecessor_template_task_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "schedule_template_tasks",
        sa.Column(
            "dependency_type",
            sa.String(length=2),
            server_default="FS",
            nullable=False,
        ),
    )
    op.add_column(
        "schedule_template_tasks",
        sa.Column(
            "lag_days",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "schedule_template_tasks",
        sa.Column("parent_template_task_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "schedule_template_tasks",
        sa.Column("order_index", sa.Integer(), nullable=True),
    )

    _migrate_tasks()
    _migrate_template_tasks()

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_predecessor_task_id_tasks",
            "tasks",
            ["predecessor_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_tasks_parent_task_id_tasks",
            "tasks",
            ["parent_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_column("predecessor")
        batch_op.drop_column("indent_level")

    with op.batch_alter_table("schedule_template_tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_template_tasks_predecessor_template_task_id",
            "schedule_template_tasks",
            ["predecessor_template_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_template_tasks_parent_template_task_id",
            "schedule_template_tasks",
            ["parent_template_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_column("predecessor")


def downgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("predecessor", sa.String(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "indent_level",
            sa.Integer(),
            server_default="0",
            nullable=True,
        ),
    )
    op.add_column(
        "schedule_template_tasks",
        sa.Column("predecessor", sa.String(), nullable=True),
    )

    _restore_legacy_tasks()
    _restore_legacy_template_tasks()

    with op.batch_alter_table("schedule_template_tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_template_tasks_parent_template_task_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_template_tasks_predecessor_template_task_id",
            type_="foreignkey",
        )
        batch_op.drop_column("order_index")
        batch_op.drop_column("parent_template_task_id")
        batch_op.drop_column("lag_days")
        batch_op.drop_column("dependency_type")
        batch_op.drop_column("predecessor_template_task_id")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_tasks_parent_task_id_tasks",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_tasks_predecessor_task_id_tasks",
            type_="foreignkey",
        )
        batch_op.drop_column("lag_days")
        batch_op.drop_column("dependency_type")
        batch_op.drop_column("predecessor_task_id")


def _migrate_tasks() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, project_id, name, predecessor, order_index,
                   parent_task_id
            FROM tasks
            """
        )
    ).mappings()
    groups = _group_rows(rows, "project_id", "order_index")

    for tasks in groups.values():
        task_ids = {task["id"] for task in tasks}
        inferred_parents = _infer_parents(tasks)

        for position, task in enumerate(tasks):
            predecessor_id, dependency_type, lag_days = _convert_predecessor(
                task["predecessor"],
                tasks,
            )
            existing_parent = task["parent_task_id"]
            parent_id = (
                existing_parent
                if existing_parent in task_ids
                else inferred_parents[position]
            )
            clean_name = (task["name"] or "").lstrip(" ")

            connection.execute(
                sa.text(
                    """
                    UPDATE tasks
                    SET name = :name,
                        predecessor_task_id = :predecessor_task_id,
                        dependency_type = :dependency_type,
                        lag_days = :lag_days,
                        parent_task_id = :parent_task_id
                    WHERE id = :id
                    """
                ),
                {
                    "id": task["id"],
                    "name": clean_name,
                    "predecessor_task_id": predecessor_id,
                    "dependency_type": dependency_type,
                    "lag_days": lag_days,
                    "parent_task_id": parent_id,
                },
            )


def _migrate_template_tasks() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, template_id, name, predecessor
            FROM schedule_template_tasks
            """
        )
    ).mappings()
    groups = _group_rows(rows, "template_id")

    for tasks in groups.values():
        inferred_parents = _infer_parents(tasks)

        for position, task in enumerate(tasks):
            predecessor_id, dependency_type, lag_days = _convert_predecessor(
                task["predecessor"],
                tasks,
            )

            connection.execute(
                sa.text(
                    """
                    UPDATE schedule_template_tasks
                    SET name = :name,
                        predecessor_template_task_id = :predecessor_id,
                        dependency_type = :dependency_type,
                        lag_days = :lag_days,
                        parent_template_task_id = :parent_id,
                        order_index = :order_index
                    WHERE id = :id
                    """
                ),
                {
                    "id": task["id"],
                    "name": (task["name"] or "").lstrip(" "),
                    "predecessor_id": predecessor_id,
                    "dependency_type": dependency_type,
                    "lag_days": lag_days,
                    "parent_id": inferred_parents[position],
                    "order_index": position + 1,
                },
            )


def _group_rows(rows, group_key: str, order_key: str | None = None):
    groups = defaultdict(list)

    for row in rows:
        groups[row[group_key]].append(dict(row))

    for group in groups.values():
        group.sort(
            key=lambda row: (
                row.get(order_key) is None if order_key else False,
                row.get(order_key) or 0 if order_key else 0,
                row["id"],
            )
        )

    return groups


def _infer_parents(tasks: list[dict]) -> list[int | None]:
    parents: list[int | None] = []
    stack: list[int] = []

    for task in tasks:
        name = task["name"] or ""
        level = (len(name) - len(name.lstrip(" "))) // 4

        if level > len(stack):
            level = len(stack)

        stack = stack[:level]
        parents.append(stack[-1] if stack else None)
        stack.append(task["id"])

    return parents


def _convert_predecessor(
    value: str | None,
    tasks: list[dict],
) -> tuple[int | None, str, int]:
    if not value:
        return None, "FS", 0

    match = PREDECESSOR_PATTERN.fullmatch(
        str(value).replace(" ", "").upper()
    )
    if match is None:
        return None, "FS", 0

    position = int(match.group(1)) - 1
    predecessor_id = (
        tasks[position]["id"]
        if 0 <= position < len(tasks)
        else None
    )
    return (
        predecessor_id,
        "SS" if match.group(2) else "FS",
        int(match.group(3) or 0),
    )


def _restore_legacy_tasks() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, project_id, name, order_index, parent_task_id,
                   predecessor_task_id, dependency_type, lag_days
            FROM tasks
            """
        )
    ).mappings()
    groups = _group_rows(rows, "project_id", "order_index")

    for tasks in groups.values():
        positions = {
            task["id"]: position
            for position, task in enumerate(tasks, start=1)
        }
        task_map = {task["id"]: task for task in tasks}

        for task in tasks:
            depth = _parent_depth(task, task_map)
            predecessor = _legacy_predecessor(task, positions)
            connection.execute(
                sa.text(
                    """
                    UPDATE tasks
                    SET name = :name,
                        predecessor = :predecessor,
                        indent_level = :indent_level
                    WHERE id = :id
                    """
                ),
                {
                    "id": task["id"],
                    "name": f"{'    ' * depth}{task['name']}",
                    "predecessor": predecessor,
                    "indent_level": depth,
                },
            )


def _restore_legacy_template_tasks() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, template_id, name, order_index,
                   parent_template_task_id,
                   predecessor_template_task_id,
                   dependency_type, lag_days
            FROM schedule_template_tasks
            """
        )
    ).mappings()
    groups = _group_rows(rows, "template_id", "order_index")

    for tasks in groups.values():
        positions = {
            task["id"]: position
            for position, task in enumerate(tasks, start=1)
        }
        task_map = {task["id"]: task for task in tasks}

        for task in tasks:
            hierarchy_task = {
                **task,
                "parent_task_id": task["parent_template_task_id"],
            }
            hierarchy_map = {
                task_id: {
                    **mapped_task,
                    "parent_task_id": mapped_task[
                        "parent_template_task_id"
                    ],
                }
                for task_id, mapped_task in task_map.items()
            }
            depth = _parent_depth(hierarchy_task, hierarchy_map)
            dependency_task = {
                **task,
                "predecessor_task_id": task[
                    "predecessor_template_task_id"
                ],
            }
            predecessor = _legacy_predecessor(
                dependency_task,
                positions,
            )
            connection.execute(
                sa.text(
                    """
                    UPDATE schedule_template_tasks
                    SET name = :name, predecessor = :predecessor
                    WHERE id = :id
                    """
                ),
                {
                    "id": task["id"],
                    "name": f"{'    ' * depth}{task['name']}",
                    "predecessor": predecessor,
                },
            )


def _parent_depth(task: dict, task_map: dict[int, dict]) -> int:
    depth = 0
    parent_id = task.get("parent_task_id")
    visited = set()

    while parent_id is not None and parent_id not in visited:
        visited.add(parent_id)
        parent = task_map.get(parent_id)
        if parent is None:
            break
        depth += 1
        parent_id = parent.get("parent_task_id")

    return depth


def _legacy_predecessor(
    task: dict,
    positions: dict[int, int],
) -> str | None:
    predecessor_id = task.get("predecessor_task_id")
    position = positions.get(predecessor_id)
    if position is None:
        return None

    relationship = "SS" if task["dependency_type"] == "SS" else ""
    lag = f"+{task['lag_days']}" if task["lag_days"] else ""
    return f"{position}{relationship}{lag}"
