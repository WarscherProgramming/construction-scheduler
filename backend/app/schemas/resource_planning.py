from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.schemas.common import MutationModel, ORMModel, UpdateMutationModel
from app.schemas.task import DateString, ProgressStatus


ResourceType = Literal["crew", "equipment"]
ResourceStatus = Literal["active", "archived"]
ResourceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
OptionalText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=2_000)
]
OptionalNotes = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=1_000)
]
PositiveId = Annotated[int, Field(ge=1, le=2_147_483_647)]
Capacity = Annotated[int, Field(ge=1, le=1_000_000)]
AvailabilityCapacity = Annotated[int, Field(ge=0, le=1_000_000)]


class CompanySummary(BaseModel):
    id: int
    name: str
    trade: str | None


class CrewCreate(MutationModel):
    name: ResourceName
    trade: Annotated[str, StringConstraints(max_length=255)] | None = None
    company_id: PositiveId | None = None
    description: OptionalText | None = None
    default_capacity: Capacity


class CrewUpdate(UpdateMutationModel):
    name: ResourceName | None = None
    trade: Annotated[str, StringConstraints(max_length=255)] | None = None
    company_id: PositiveId | None = None
    description: OptionalText | None = None
    default_capacity: Capacity | None = None

    @field_validator("name", "default_capacity")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class CrewResponse(BaseModel):
    id: int
    project_id: int
    name: str
    trade: str | None
    company: CompanySummary | None
    description: str | None
    default_capacity: int
    capacity_unit: Literal["workers"]
    status: ResourceStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class CrewMutationResponse(BaseModel):
    crew: CrewResponse


class CrewListResponse(BaseModel):
    crews: list[CrewResponse]
    total: int
    limit: int
    offset: int


class EquipmentResourceCreate(MutationModel):
    name: ResourceName
    equipment_type: ResourceName
    identifier: ResourceName | None = None
    description: OptionalText | None = None
    default_capacity: Capacity = 1


class EquipmentResourceUpdate(UpdateMutationModel):
    name: ResourceName | None = None
    equipment_type: ResourceName | None = None
    identifier: ResourceName | None = None
    description: OptionalText | None = None
    default_capacity: Capacity | None = None

    @field_validator("name", "equipment_type", "default_capacity")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class EquipmentResourceResponse(ORMModel):
    id: int
    project_id: int
    name: str
    equipment_type: str
    identifier: str | None
    description: str | None
    default_capacity: int
    capacity_unit: Literal["units"]
    status: ResourceStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class EquipmentResourceMutationResponse(BaseModel):
    equipment: EquipmentResourceResponse


class EquipmentResourceListResponse(BaseModel):
    equipment: list[EquipmentResourceResponse]
    total: int
    limit: int
    offset: int


class AssignmentCreate(MutationModel):
    resource_type: ResourceType
    resource_id: PositiveId
    allocation_amount: Capacity
    notes: OptionalNotes | None = None


class AssignmentUpdate(UpdateMutationModel):
    allocation_amount: Capacity | None = None
    notes: OptionalNotes | None = None

    @field_validator("allocation_amount")
    @classmethod
    def allocation_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class AssignmentResourceSummary(BaseModel):
    id: int
    resource_type: ResourceType
    name: str
    detail: str | None
    identifier: str | None
    status: ResourceStatus
    default_capacity: int
    capacity_unit: Literal["workers", "units"]


class AssignmentResponse(BaseModel):
    id: int
    project_id: int
    task_id: int
    resource: AssignmentResourceSummary
    allocation_amount: int
    allocation_unit: Literal["workers", "units"]
    notes: str | None
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class AssignmentMutationResponse(BaseModel):
    assignment: AssignmentResponse


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]


class AvailabilityCreate(MutationModel):
    start_date: DateString
    end_date: DateString
    capacity: AvailabilityCapacity
    notes: OptionalNotes | None = None

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


class AvailabilityUpdate(UpdateMutationModel):
    start_date: DateString | None = None
    end_date: DateString | None = None
    capacity: AvailabilityCapacity | None = None
    notes: OptionalNotes | None = None

    @field_validator("start_date", "end_date", "capacity")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class AvailabilityResponse(ORMModel):
    id: int
    project_id: int
    resource_type: ResourceType
    start_date: str
    end_date: str
    capacity: int
    notes: str | None
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class AvailabilityMutationResponse(BaseModel):
    availability: AvailabilityResponse


class AvailabilityListResponse(BaseModel):
    availability: list[AvailabilityResponse]
    total: int
    limit: int
    offset: int


class LoadingTaskSummary(BaseModel):
    id: int
    wbs: str | None
    name: str | None
    start_date: str | None
    end_date: str | None
    progress_status: ProgressStatus
    is_critical: bool


class LoadingDayResponse(BaseModel):
    date: str
    demand: int
    capacity: int
    available_remainder: int
    utilization_percent: float | None
    overage: int
    status: Literal["within_capacity", "over_allocated", "unavailable"]


class LoadingResourceResponse(BaseModel):
    resource: AssignmentResourceSummary
    company: CompanySummary | None = None
    trade: str | None = None
    days: list[LoadingDayResponse]
    peak_demand: int
    average_demand: float
    over_allocated_days: int
    unavailable_days: int


class LoadingConflictResponse(BaseModel):
    date: str
    resource: AssignmentResourceSummary
    demand: int
    capacity: int
    overage: int
    status: Literal["over_allocated", "unavailable"]
    message: str
    contributing_tasks: list[LoadingTaskSummary]
    contributing_task_count: int
    contributing_tasks_truncated: bool


class UnassignedTaskResponse(LoadingTaskSummary):
    reason: Literal["No planned resource assignment."]
    unscheduled: bool


class EquipmentTypePeak(BaseModel):
    equipment_type: str
    peak_demand: int


class ResourceLoadingSummary(BaseModel):
    active_crews: int
    active_equipment_resources: int
    assigned_tasks: int
    unassigned_executable_tasks: int
    unscheduled_tasks: int
    over_allocated_resource_days: int
    labor_overallocated_days: int
    equipment_overallocated_days: int
    unavailable_resource_conflicts: int
    look_ahead_over_allocation_count: int
    peak_labor_demand: int
    average_labor_demand: float
    equipment_type_peaks: list[EquipmentTypePeak]


class ResourceLoadingResponse(BaseModel):
    project_id: int
    data_date: str
    start_date: str
    end_date: str
    summary: ResourceLoadingSummary
    resources: list[LoadingResourceResponse]
    conflicts: list[LoadingConflictResponse]
    unassigned_tasks: list[UnassignedTaskResponse]
    total_conflicts: int
    conflict_limit: int
    conflicts_truncated: bool
    total_resources: int
    limit: int
    offset: int
