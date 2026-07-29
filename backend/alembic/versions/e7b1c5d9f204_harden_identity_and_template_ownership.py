"""Harden identity normalization and template ownership.

Revision ID: e7b1c5d9f204
Revises: c4d8e2f6a1b3
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e7b1c5d9f204"
down_revision: str | Sequence[str] | None = "c4d8e2f6a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_existing_emails() -> None:
    connection = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
    )
    rows = connection.execute(
        sa.select(users.c.id, users.c.email).order_by(users.c.id)
    ).all()

    normalized_owners: dict[str, int] = {}
    normalized_rows: list[tuple[int, str]] = []
    for user_id, email in rows:
        normalized = str(email).strip().lower()
        if normalized.count("@") != 1 or any(
            character.isspace() for character in normalized
        ):
            raise RuntimeError(
                "Invalid stored emails must be resolved before upgrade"
            )
        if normalized in normalized_owners:
            raise RuntimeError(
                "Canonical email collisions must be resolved before upgrade"
            )
        normalized_owners[normalized] = user_id
        normalized_rows.append((user_id, normalized))

    for user_id, normalized in normalized_rows:
        connection.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(email=normalized)
        )


def upgrade() -> None:
    _normalize_existing_emails()

    with op.batch_alter_table("schedule_templates") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_schedule_templates_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_schedule_templates_user_id",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("schedule_templates") as batch_op:
        batch_op.drop_index("ix_schedule_templates_user_id")
        batch_op.drop_constraint(
            "fk_schedule_templates_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("user_id")
