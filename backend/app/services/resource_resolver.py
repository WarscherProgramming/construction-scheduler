from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.resource_planning import Crew, EquipmentResource


ResourceType = Literal["crew", "equipment"]


@dataclass(frozen=True)
class ResourceDefinition:
    model: type[Crew] | type[EquipmentResource]
    label: str
    capacity_unit: str
    reference_field: str


RESOURCE_DEFINITIONS: dict[ResourceType, ResourceDefinition] = {
    "crew": ResourceDefinition(Crew, "Crew", "workers", "crew_id"),
    "equipment": ResourceDefinition(
        EquipmentResource,
        "Equipment resource",
        "units",
        "equipment_resource_id",
    ),
}


def resource_definition(resource_type: ResourceType) -> ResourceDefinition:
    definition = RESOURCE_DEFINITIONS.get(resource_type)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported resource type",
        )
    return definition


def get_project_resource(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    for_update: bool = False,
) -> Crew | EquipmentResource:
    definition = resource_definition(resource_type)
    query = db.query(definition.model).filter(
        definition.model.id == resource_id,
        definition.model.project_id == project_id,
    )
    if for_update:
        query = query.with_for_update()
    resource = query.first()
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{definition.label} not found",
        )
    return resource


def ensure_active(resource: Crew | EquipmentResource) -> None:
    if resource.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived resources cannot be changed or newly assigned",
        )


def typed_reference(resource_type: ResourceType, resource_id: int) -> dict:
    definition = resource_definition(resource_type)
    return {
        "resource_type": resource_type,
        "crew_id": resource_id if definition.reference_field == "crew_id" else None,
        "equipment_resource_id": (
            resource_id if definition.reference_field == "equipment_resource_id" else None
        ),
    }
