"""enhance change orders

Revision ID: f2a8c1d4e6b0
Revises: d94f7a2b6e31
Create Date: 2026-07-26
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a8c1d4e6b0"
down_revision: Union[str, Sequence[str], None] = "d94f7a2b6e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NUMBER_PATTERN = re.compile(r"^CO-(\d+)$")
MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY_VALUE = Decimal("999999999999.99")


def _parse_legacy_amount(value: str | None) -> Decimal | None:
    if value is None:
        return None

    normalized = value.strip().replace("$", "").replace(",", "")
    if not normalized:
        return None

    try:
        amount = Decimal(normalized)
        quantized_amount = amount.quantize(MONEY_QUANTUM)
    except InvalidOperation:
        return None

    if (
        not amount.is_finite()
        or amount < 0
        or amount > MAX_MONEY_VALUE
        or amount != quantized_amount
    ):
        return None

    return amount


def _normalize_numbers_and_collect_sequences(bind) -> dict[int, int]:
    change_orders = sa.table(
        "change_orders",
        sa.column("id", sa.Integer),
        sa.column("project_id", sa.Integer),
        sa.column("co_number", sa.String),
    )
    rows = bind.execute(
        sa.select(
            change_orders.c.id,
            change_orders.c.project_id,
            change_orders.c.co_number,
        ).order_by(change_orders.c.project_id, change_orders.c.id)
    ).mappings()

    project_rows: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        project_rows[row["project_id"]].append(dict(row))

    sequence_values: dict[int, int] = {}
    for project_id, records in project_rows.items():
        used_numbers = {
            record["co_number"]
            for record in records
            if record["co_number"] and record["co_number"].strip()
        }
        valid_suffixes = [
            int(match.group(1))
            for record in records
            if record["co_number"]
            and (
                match := NUMBER_PATTERN.fullmatch(record["co_number"])
            )
        ]
        next_number = max(valid_suffixes, default=0) + 1
        seen_numbers: set[str] = set()

        for record in records:
            number = record["co_number"]
            needs_number = (
                not number
                or not number.strip()
                or number in seen_numbers
            )

            if needs_number:
                candidate = f"CO-{next_number:03d}"
                while candidate in used_numbers:
                    next_number += 1
                    candidate = f"CO-{next_number:03d}"

                bind.execute(
                    change_orders.update()
                    .where(change_orders.c.id == record["id"])
                    .values(co_number=candidate)
                )
                number = candidate
                used_numbers.add(candidate)
                next_number += 1

            seen_numbers.add(number)

        sequence_values[project_id] = next_number - 1

    return sequence_values


def _backfill_safe_amounts(bind) -> None:
    change_orders = sa.table(
        "change_orders",
        sa.column("id", sa.Integer),
        sa.column("amount", sa.String),
        sa.column("proposed_amount", sa.Numeric(14, 2)),
    )

    rows = bind.execute(
        sa.select(change_orders.c.id, change_orders.c.amount)
    ).mappings()
    for row in rows:
        proposed_amount = _parse_legacy_amount(row["amount"])
        if proposed_amount is None:
            continue

        bind.execute(
            change_orders.update()
            .where(change_orders.c.id == row["id"])
            .values(proposed_amount=proposed_amount)
        )


def upgrade() -> None:
    op.add_column(
        "change_orders",
        sa.Column("title", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column(
            "proposed_amount",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "change_orders",
        sa.Column(
            "approved_amount",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "change_orders",
        sa.Column("schedule_impact_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("requested_date", sa.String(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("submitted_date", sa.String(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("approved_date", sa.String(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("executed_date", sa.String(), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    sequence_values = _normalize_numbers_and_collect_sequences(bind)
    _backfill_safe_amounts(bind)
    op.execute(
        sa.text(
            """
            UPDATE change_orders
            SET created_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL OR updated_at IS NULL
            """
        )
    )

    op.create_table(
        "change_order_number_sequences",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )

    sequence_table = sa.table(
        "change_order_number_sequences",
        sa.column("project_id", sa.Integer),
        sa.column("last_number", sa.Integer),
    )
    if sequence_values:
        op.bulk_insert(
            sequence_table,
            [
                {
                    "project_id": project_id,
                    "last_number": last_number,
                }
                for project_id, last_number in sorted(
                    sequence_values.items()
                )
            ],
        )

    with op.batch_alter_table("change_orders") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.create_unique_constraint(
            "uq_change_orders_project_id_co_number",
            ["project_id", "co_number"],
        )


def downgrade() -> None:
    with op.batch_alter_table("change_orders") as batch_op:
        batch_op.drop_constraint(
            "uq_change_orders_project_id_co_number",
            type_="unique",
        )

    op.drop_table("change_order_number_sequences")

    with op.batch_alter_table("change_orders") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("executed_date")
        batch_op.drop_column("approved_date")
        batch_op.drop_column("submitted_date")
        batch_op.drop_column("requested_date")
        batch_op.drop_column("schedule_impact_days")
        batch_op.drop_column("approved_amount")
        batch_op.drop_column("proposed_amount")
        batch_op.drop_column("reason")
        batch_op.drop_column("title")
