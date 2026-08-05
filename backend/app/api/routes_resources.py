from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import PositiveId, get_db, get_owned_project
from app.core.security import get_current_user
from app.models.project import Project
from app.schemas.common import MessageResponse
from app.schemas.resource_planning import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentMutationResponse,
    AssignmentUpdate,
    AvailabilityCreate,
    AvailabilityListResponse,
    AvailabilityMutationResponse,
    AvailabilityUpdate,
    CrewCreate,
    CrewListResponse,
    CrewMutationResponse,
    CrewUpdate,
    DateString,
    EquipmentResourceCreate,
    EquipmentResourceListResponse,
    EquipmentResourceMutationResponse,
    EquipmentResourceUpdate,
    ResourceLoadingResponse,
    ResourceType,
)
from app.services.resource_planning import (
    archive_crew,
    archive_equipment,
    create_assignment,
    create_availability,
    create_crew,
    create_equipment,
    delete_assignment,
    delete_availability,
    get_crew,
    get_equipment,
    get_resource_loading,
    list_availability,
    list_crews,
    list_equipment,
    list_task_assignments,
    update_assignment,
    update_availability,
    update_crew,
    update_equipment,
)


router = APIRouter()
StatusFilter = Literal["active", "archived", "all"]


@router.post("/projects/{project_id}/crews", response_model=CrewMutationResponse, status_code=201)
def create_project_crew(
    project_id: int,
    payload: CrewCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"crew": create_crew(
        db, project_id=project_id, created_by=current_user["id"], values=payload.model_dump()
    )}


@router.get("/projects/{project_id}/crews", response_model=CrewListResponse)
def get_project_crews(
    project_id: int,
    resource_status: Annotated[StatusFilter, Query(alias="status")] = "all",
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return list_crews(
        db, project_id=project_id, status_filter=resource_status, limit=limit, offset=offset
    )


@router.get("/projects/{project_id}/crews/{crew_id}", response_model=CrewMutationResponse)
def get_project_crew(
    project_id: int,
    crew_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"crew": get_crew(db, project_id=project_id, crew_id=crew_id)}


@router.put("/projects/{project_id}/crews/{crew_id}", response_model=CrewMutationResponse)
def update_project_crew(
    project_id: int,
    crew_id: PositiveId,
    payload: CrewUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"crew": update_crew(
        db, project_id=project_id, crew_id=crew_id, values=payload.model_dump(exclude_unset=True)
    )}


@router.post("/projects/{project_id}/crews/{crew_id}/archive", response_model=CrewMutationResponse)
def archive_project_crew(
    project_id: int,
    crew_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"crew": archive_crew(db, project_id=project_id, crew_id=crew_id)}


@router.post(
    "/projects/{project_id}/equipment-resources",
    response_model=EquipmentResourceMutationResponse,
    status_code=201,
)
def create_project_equipment(
    project_id: int,
    payload: EquipmentResourceCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"equipment": create_equipment(
        db, project_id=project_id, created_by=current_user["id"], values=payload.model_dump()
    )}


@router.get(
    "/projects/{project_id}/equipment-resources",
    response_model=EquipmentResourceListResponse,
)
def get_project_equipment_list(
    project_id: int,
    resource_status: Annotated[StatusFilter, Query(alias="status")] = "all",
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return list_equipment(
        db, project_id=project_id, status_filter=resource_status, limit=limit, offset=offset
    )


@router.get(
    "/projects/{project_id}/equipment-resources/{equipment_id}",
    response_model=EquipmentResourceMutationResponse,
)
def get_project_equipment(
    project_id: int,
    equipment_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"equipment": get_equipment(
        db, project_id=project_id, equipment_id=equipment_id
    )}


@router.put(
    "/projects/{project_id}/equipment-resources/{equipment_id}",
    response_model=EquipmentResourceMutationResponse,
)
def update_project_equipment(
    project_id: int,
    equipment_id: PositiveId,
    payload: EquipmentResourceUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"equipment": update_equipment(
        db,
        project_id=project_id,
        equipment_id=equipment_id,
        values=payload.model_dump(exclude_unset=True),
    )}


@router.post(
    "/projects/{project_id}/equipment-resources/{equipment_id}/archive",
    response_model=EquipmentResourceMutationResponse,
)
def archive_project_equipment(
    project_id: int,
    equipment_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return {"equipment": archive_equipment(
        db, project_id=project_id, equipment_id=equipment_id
    )}


@router.get(
    "/projects/{project_id}/tasks/{task_id}/resource-assignments",
    response_model=AssignmentListResponse,
)
def get_task_resource_assignments(
    project_id: int,
    task_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return list_task_assignments(db, project_id=project_id, task_id=task_id)


@router.post(
    "/projects/{project_id}/tasks/{task_id}/resource-assignments",
    response_model=AssignmentMutationResponse,
    status_code=201,
)
def create_task_resource_assignment(
    project_id: int,
    task_id: PositiveId,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"assignment": create_assignment(
        db,
        project_id=project_id,
        task_id=task_id,
        created_by=current_user["id"],
        values=payload.model_dump(),
    )}


@router.put(
    "/projects/{project_id}/tasks/{task_id}/resource-assignments/{assignment_id}",
    response_model=AssignmentMutationResponse,
)
def update_task_resource_assignment(
    project_id: int,
    task_id: PositiveId,
    assignment_id: PositiveId,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"assignment": update_assignment(
        db,
        project_id=project_id,
        task_id=task_id,
        assignment_id=assignment_id,
        updated_by=current_user["id"],
        values=payload.model_dump(exclude_unset=True),
    )}


@router.delete(
    "/projects/{project_id}/tasks/{task_id}/resource-assignments/{assignment_id}",
    response_model=MessageResponse,
)
def delete_task_resource_assignment(
    project_id: int,
    task_id: PositiveId,
    assignment_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    delete_assignment(
        db, project_id=project_id, task_id=task_id, assignment_id=assignment_id
    )
    return {"message": "Resource assignment deleted"}


@router.get(
    "/projects/{project_id}/resources/{resource_type}/{resource_id}/availability",
    response_model=AvailabilityListResponse,
)
def get_resource_availability(
    project_id: int,
    resource_type: ResourceType,
    resource_id: PositiveId,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return list_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/resources/{resource_type}/{resource_id}/availability",
    response_model=AvailabilityMutationResponse,
    status_code=201,
)
def create_resource_availability(
    project_id: int,
    resource_type: ResourceType,
    resource_id: PositiveId,
    payload: AvailabilityCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"availability": create_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=current_user["id"],
        values=payload.model_dump(),
    )}


@router.put(
    "/projects/{project_id}/resources/{resource_type}/{resource_id}/availability/{availability_id}",
    response_model=AvailabilityMutationResponse,
)
def update_resource_availability(
    project_id: int,
    resource_type: ResourceType,
    resource_id: PositiveId,
    availability_id: PositiveId,
    payload: AvailabilityUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    current_user: dict = Depends(get_current_user),
):
    return {"availability": update_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        availability_id=availability_id,
        updated_by=current_user["id"],
        values=payload.model_dump(exclude_unset=True),
    )}


@router.delete(
    "/projects/{project_id}/resources/{resource_type}/{resource_id}/availability/{availability_id}",
    response_model=MessageResponse,
)
def delete_resource_availability(
    project_id: int,
    resource_type: ResourceType,
    resource_id: PositiveId,
    availability_id: PositiveId,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    delete_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        availability_id=availability_id,
    )
    return {"message": "Availability override deleted"}


@router.get("/projects/{project_id}/resource-loading", response_model=ResourceLoadingResponse)
def get_project_resource_loading(
    project_id: int,
    start_date: Annotated[DateString | None, Query()] = None,
    end_date: Annotated[DateString | None, Query()] = None,
    resource_type: Annotated[ResourceType | None, Query()] = None,
    resource_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    company_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    trade: Annotated[str | None, Query(max_length=255)] = None,
    over_allocated_only: bool = False,
    include_unassigned: bool = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    return get_resource_loading(
        db,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        resource_type=resource_type,
        resource_id=resource_id,
        company_id=company_id,
        trade=trade,
        over_allocated_only=over_allocated_only,
        include_unassigned=include_unassigned,
        limit=limit,
        offset=offset,
    )
