"""Normalize drawing issue membership uniqueness.

Revision ID: c8f1a4d7e290
Revises: b7e4f2a9c631
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c8f1a4d7e290"
down_revision: str | Sequence[str] | None = "b7e4f2a9c631"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_NAME = "drawing_issue_revisions"
LEGACY_UNIQUE_NAME = "uq_drawing_issue_revisions_membership"
PRIMARY_KEY_COLUMNS = ["drawing_issue_id", "drawing_revision_id"]


def _constraint_state() -> tuple[sa.engine.Connection, dict, set[str]]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    primary_key = inspector.get_pk_constraint(TABLE_NAME)
    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
        if constraint["name"] is not None
    }
    if primary_key.get("constrained_columns") != PRIMARY_KEY_COLUMNS:
        raise RuntimeError(
            "drawing_issue_revisions must retain its composite primary key"
        )
    return bind, primary_key, unique_names


def upgrade() -> None:
    bind, _, unique_names = _constraint_state()
    if LEGACY_UNIQUE_NAME not in unique_names:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.drop_constraint(LEGACY_UNIQUE_NAME, type_="unique")
        return

    op.drop_constraint(LEGACY_UNIQUE_NAME, TABLE_NAME, type_="unique")


def downgrade() -> None:
    bind, primary_key, unique_names = _constraint_state()
    if (
        LEGACY_UNIQUE_NAME in unique_names
        or primary_key.get("name") == LEGACY_UNIQUE_NAME
    ):
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.create_unique_constraint(
                LEGACY_UNIQUE_NAME,
                PRIMARY_KEY_COLUMNS,
            )
        return

    op.create_unique_constraint(
        LEGACY_UNIQUE_NAME,
        TABLE_NAME,
        PRIMARY_KEY_COLUMNS,
    )
