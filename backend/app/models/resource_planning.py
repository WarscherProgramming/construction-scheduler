from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Crew(Base):
    __tablename__ = "crews"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_crews_name_nonblank"),
        CheckConstraint(
            "default_capacity >= 1 AND default_capacity <= 1000000",
            name="ck_crews_default_capacity",
        ),
        CheckConstraint("capacity_unit = 'workers'", name="ck_crews_capacity_unit"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_crews_status"),
        UniqueConstraint("project_id", "normalized_name", name="uq_crews_project_name"),
        Index("ix_crews_project_status_name", "project_id", "status", "name", "id"),
        Index("ix_crews_project_company", "project_id", "company_id", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    trade = Column(String(255), nullable=True)
    company_id = Column(
        Integer,
        ForeignKey("project_companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    description = Column(String(2_000), nullable=True)
    default_capacity = Column(Integer, nullable=False)
    capacity_unit = Column(
        String(16), nullable=False, default="workers", server_default=text("'workers'")
    )
    status = Column(
        String(16), nullable=False, default="active", server_default=text("'active'")
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)


class EquipmentResource(Base):
    __tablename__ = "equipment_resources"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0", name="ck_equipment_resources_name_nonblank"
        ),
        CheckConstraint(
            "length(trim(equipment_type)) > 0",
            name="ck_equipment_resources_type_nonblank",
        ),
        CheckConstraint(
            "default_capacity >= 1 AND default_capacity <= 1000000",
            name="ck_equipment_resources_default_capacity",
        ),
        CheckConstraint(
            "capacity_unit = 'units'", name="ck_equipment_resources_capacity_unit"
        ),
        CheckConstraint(
            "status IN ('active', 'archived')", name="ck_equipment_resources_status"
        ),
        UniqueConstraint(
            "project_id", "normalized_name", name="uq_equipment_resources_project_name"
        ),
        UniqueConstraint(
            "project_id",
            "normalized_identifier",
            name="uq_equipment_resources_project_identifier",
        ),
        Index(
            "ix_equipment_resources_project_status_name",
            "project_id",
            "status",
            "name",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(240), nullable=False)
    equipment_type = Column(String(120), nullable=False)
    identifier = Column(String(120), nullable=True)
    normalized_identifier = Column(String(240), nullable=True)
    description = Column(String(2_000), nullable=True)
    default_capacity = Column(Integer, nullable=False, default=1, server_default=text("1"))
    capacity_unit = Column(
        String(16), nullable=False, default="units", server_default=text("'units'")
    )
    status = Column(
        String(16), nullable=False, default="active", server_default=text("'active'")
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)


class TaskResourceAssignment(Base):
    __tablename__ = "task_resource_assignments"
    __table_args__ = (
        CheckConstraint(
            "(resource_type = 'crew' AND crew_id IS NOT NULL "
            "AND equipment_resource_id IS NULL AND allocation_unit = 'workers') OR "
            "(resource_type = 'equipment' AND crew_id IS NULL "
            "AND equipment_resource_id IS NOT NULL AND allocation_unit = 'units')",
            name="ck_task_resource_assignments_typed_reference",
        ),
        CheckConstraint(
            "allocation_amount >= 1 AND allocation_amount <= 1000000",
            name="ck_task_resource_assignments_allocation",
        ),
        UniqueConstraint(
            "task_id", "crew_id", name="uq_task_resource_assignments_task_crew"
        ),
        UniqueConstraint(
            "task_id",
            "equipment_resource_id",
            name="uq_task_resource_assignments_task_equipment",
        ),
        Index("ix_task_resource_assignments_project_task", "project_id", "task_id", "id"),
        Index("ix_task_resource_assignments_project_crew", "project_id", "crew_id", "id"),
        Index(
            "ix_task_resource_assignments_project_equipment",
            "project_id",
            "equipment_resource_id",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(16), nullable=False)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=True)
    equipment_resource_id = Column(
        Integer, ForeignKey("equipment_resources.id"), nullable=True
    )
    allocation_amount = Column(Integer, nullable=False)
    allocation_unit = Column(String(16), nullable=False)
    notes = Column(String(1_000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class ResourceAvailability(Base):
    __tablename__ = "resource_availability"
    __table_args__ = (
        CheckConstraint(
            "(resource_type = 'crew' AND crew_id IS NOT NULL "
            "AND equipment_resource_id IS NULL) OR "
            "(resource_type = 'equipment' AND crew_id IS NULL "
            "AND equipment_resource_id IS NOT NULL)",
            name="ck_resource_availability_typed_reference",
        ),
        CheckConstraint("start_date <= end_date", name="ck_resource_availability_date_order"),
        CheckConstraint(
            "capacity >= 0 AND capacity <= 1000000",
            name="ck_resource_availability_capacity",
        ),
        UniqueConstraint(
            "crew_id",
            "start_date",
            "end_date",
            name="uq_resource_availability_crew_range",
        ),
        UniqueConstraint(
            "equipment_resource_id",
            "start_date",
            "end_date",
            name="uq_resource_availability_equipment_range",
        ),
        Index(
            "ix_resource_availability_project_crew_dates",
            "project_id",
            "crew_id",
            "start_date",
            "end_date",
        ),
        Index(
            "ix_resource_availability_project_equipment_dates",
            "project_id",
            "equipment_resource_id",
            "start_date",
            "end_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(16), nullable=False)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=True)
    equipment_resource_id = Column(
        Integer, ForeignKey("equipment_resources.id"), nullable=True
    )
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    capacity = Column(Integer, nullable=False)
    notes = Column(String(1_000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
