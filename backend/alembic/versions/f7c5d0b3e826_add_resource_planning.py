"""Add crew, equipment, assignment, and availability planning.

Revision ID: f7c5d0b3e826
Revises: e6b4c9a2d715
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f7c5d0b3e826"
down_revision: str | Sequence[str] | None = "e6b4c9a2d715"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("trade", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("default_capacity", sa.Integer(), nullable=False),
        sa.Column("capacity_unit", sa.String(length=16), server_default=sa.text("'workers'"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_crews_name_nonblank"),
        sa.CheckConstraint("default_capacity >= 1 AND default_capacity <= 1000000", name="ck_crews_default_capacity"),
        sa.CheckConstraint("capacity_unit = 'workers'", name="ck_crews_capacity_unit"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_crews_status"),
        sa.ForeignKeyConstraint(["company_id"], ["project_companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "normalized_name", name="uq_crews_project_name"),
    )
    op.create_index("ix_crews_id", "crews", ["id"])
    op.create_index("ix_crews_project_company", "crews", ["project_id", "company_id", "id"])
    op.create_index("ix_crews_project_status_name", "crews", ["project_id", "status", "name", "id"])

    op.create_table(
        "equipment_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("equipment_type", sa.String(length=120), nullable=False),
        sa.Column("identifier", sa.String(length=120), nullable=True),
        sa.Column("normalized_identifier", sa.String(length=240), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("default_capacity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("capacity_unit", sa.String(length=16), server_default=sa.text("'units'"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_equipment_resources_name_nonblank"),
        sa.CheckConstraint("length(trim(equipment_type)) > 0", name="ck_equipment_resources_type_nonblank"),
        sa.CheckConstraint("default_capacity >= 1 AND default_capacity <= 1000000", name="ck_equipment_resources_default_capacity"),
        sa.CheckConstraint("capacity_unit = 'units'", name="ck_equipment_resources_capacity_unit"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_equipment_resources_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "normalized_identifier", name="uq_equipment_resources_project_identifier"),
        sa.UniqueConstraint("project_id", "normalized_name", name="uq_equipment_resources_project_name"),
    )
    op.create_index("ix_equipment_resources_id", "equipment_resources", ["id"])
    op.create_index("ix_equipment_resources_project_status_name", "equipment_resources", ["project_id", "status", "name", "id"])

    op.create_table(
        "task_resource_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=16), nullable=False),
        sa.Column("crew_id", sa.Integer(), nullable=True),
        sa.Column("equipment_resource_id", sa.Integer(), nullable=True),
        sa.Column("allocation_amount", sa.Integer(), nullable=False),
        sa.Column("allocation_unit", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(resource_type = 'crew' AND crew_id IS NOT NULL AND equipment_resource_id IS NULL AND allocation_unit = 'workers') OR "
            "(resource_type = 'equipment' AND crew_id IS NULL AND equipment_resource_id IS NOT NULL AND allocation_unit = 'units')",
            name="ck_task_resource_assignments_typed_reference",
        ),
        sa.CheckConstraint("allocation_amount >= 1 AND allocation_amount <= 1000000", name="ck_task_resource_assignments_allocation"),
        sa.ForeignKeyConstraint(["crew_id"], ["crews.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["equipment_resource_id"], ["equipment_resources.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "crew_id", name="uq_task_resource_assignments_task_crew"),
        sa.UniqueConstraint("task_id", "equipment_resource_id", name="uq_task_resource_assignments_task_equipment"),
    )
    op.create_index("ix_task_resource_assignments_id", "task_resource_assignments", ["id"])
    op.create_index("ix_task_resource_assignments_project_crew", "task_resource_assignments", ["project_id", "crew_id", "id"])
    op.create_index("ix_task_resource_assignments_project_equipment", "task_resource_assignments", ["project_id", "equipment_resource_id", "id"])
    op.create_index("ix_task_resource_assignments_project_task", "task_resource_assignments", ["project_id", "task_id", "id"])

    op.create_table(
        "resource_availability",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=16), nullable=False),
        sa.Column("crew_id", sa.Integer(), nullable=True),
        sa.Column("equipment_resource_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.String(length=10), nullable=False),
        sa.Column("end_date", sa.String(length=10), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(resource_type = 'crew' AND crew_id IS NOT NULL AND equipment_resource_id IS NULL) OR "
            "(resource_type = 'equipment' AND crew_id IS NULL AND equipment_resource_id IS NOT NULL)",
            name="ck_resource_availability_typed_reference",
        ),
        sa.CheckConstraint("start_date <= end_date", name="ck_resource_availability_date_order"),
        sa.CheckConstraint("capacity >= 0 AND capacity <= 1000000", name="ck_resource_availability_capacity"),
        sa.ForeignKeyConstraint(["crew_id"], ["crews.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["equipment_resource_id"], ["equipment_resources.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crew_id", "start_date", "end_date", name="uq_resource_availability_crew_range"),
        sa.UniqueConstraint("equipment_resource_id", "start_date", "end_date", name="uq_resource_availability_equipment_range"),
    )
    op.create_index("ix_resource_availability_id", "resource_availability", ["id"])
    op.create_index("ix_resource_availability_project_crew_dates", "resource_availability", ["project_id", "crew_id", "start_date", "end_date"])
    op.create_index("ix_resource_availability_project_equipment_dates", "resource_availability", ["project_id", "equipment_resource_id", "start_date", "end_date"])


def downgrade() -> None:
    op.drop_index("ix_resource_availability_project_equipment_dates", table_name="resource_availability")
    op.drop_index("ix_resource_availability_project_crew_dates", table_name="resource_availability")
    op.drop_index("ix_resource_availability_id", table_name="resource_availability")
    op.drop_table("resource_availability")
    op.drop_index("ix_task_resource_assignments_project_task", table_name="task_resource_assignments")
    op.drop_index("ix_task_resource_assignments_project_equipment", table_name="task_resource_assignments")
    op.drop_index("ix_task_resource_assignments_project_crew", table_name="task_resource_assignments")
    op.drop_index("ix_task_resource_assignments_id", table_name="task_resource_assignments")
    op.drop_table("task_resource_assignments")
    op.drop_index("ix_equipment_resources_project_status_name", table_name="equipment_resources")
    op.drop_index("ix_equipment_resources_id", table_name="equipment_resources")
    op.drop_table("equipment_resources")
    op.drop_index("ix_crews_project_status_name", table_name="crews")
    op.drop_index("ix_crews_project_company", table_name="crews")
    op.drop_index("ix_crews_id", table_name="crews")
    op.drop_table("crews")
