"""Add preconstruction execution metrics and cost accounting.

Revision ID: f3d6a8b2c517
Revises: e2b8d4f7c103
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3d6a8b2c517"
down_revision: str | Sequence[str] | None = "e2b8d4f7c103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EXECUTION_KIND_SQL = (
    "execution_kind IN ('preparation_run', 'analysis_attempt', "
    "'scope_comparison', 'evaluation_run')"
)
BUDGET_REASON_SQL = (
    "budget_stop_reason IS NULL OR budget_stop_reason IN "
    "('pair_budget_exceeded', 'assertion_budget_exceeded', "
    "'runtime_budget_exceeded', 'candidate_limit_reached', "
    "'finding_limit_reached')"
)


def upgrade() -> None:
    op.create_table(
        "preconstruction_execution_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("execution_kind", sa.String(length=32), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("metrics_version", sa.String(length=100), nullable=False),
        sa.Column(
            "duration_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("phase_durations_json", sa.Text(), nullable=True),
        sa.Column("query_count", sa.Integer(), nullable=True),
        sa.Column("response_bytes", sa.Integer(), nullable=True),
        sa.Column("input_units", sa.Integer(), nullable=True),
        sa.Column("output_units", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_micros", sa.Integer(), nullable=True),
        sa.Column(
            "manifest_reused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("budget_stop_reason", sa.String(length=50), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            EXECUTION_KIND_SQL,
            name="ck_preconstruction_execution_metrics_kind",
        ),
        sa.CheckConstraint(
            "execution_id > 0 AND duration_ms >= 0",
            name="ck_preconstruction_execution_metrics_positive",
        ),
        sa.CheckConstraint(
            "query_count IS NULL OR query_count >= 0",
            name="ck_preconstruction_execution_metrics_query_count",
        ),
        sa.CheckConstraint(
            "response_bytes IS NULL OR response_bytes >= 0",
            name="ck_preconstruction_execution_metrics_response_bytes",
        ),
        sa.CheckConstraint(
            "input_units IS NULL OR input_units >= 0",
            name="ck_preconstruction_execution_metrics_input_units",
        ),
        sa.CheckConstraint(
            "output_units IS NULL OR output_units >= 0",
            name="ck_preconstruction_execution_metrics_output_units",
        ),
        sa.CheckConstraint(
            "estimated_cost_micros IS NULL OR estimated_cost_micros >= 0",
            name="ck_preconstruction_execution_metrics_cost",
        ),
        sa.CheckConstraint(
            BUDGET_REASON_SQL,
            name="ck_preconstruction_execution_metrics_budget_reason",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_kind",
            "execution_id",
            name="uq_preconstruction_execution_metrics_execution",
        ),
    )
    op.create_index(
        "ix_preconstruction_execution_metrics_id",
        "preconstruction_execution_metrics",
        ["id"],
    )
    op.create_index(
        "ix_preconstruction_execution_metrics_project_listing",
        "preconstruction_execution_metrics",
        ["project_id", "execution_kind", "recorded_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_preconstruction_execution_metrics_project_listing",
        table_name="preconstruction_execution_metrics",
    )
    op.drop_index(
        "ix_preconstruction_execution_metrics_id",
        table_name="preconstruction_execution_metrics",
    )
    op.drop_table("preconstruction_execution_metrics")
