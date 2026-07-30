
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import (
    CollectionPage,
    get_collection_page,
    get_db,
    get_owned_project,
)
from app.models.inspection import Inspection
from app.models.project import Project
from app.schemas.inspection import (
    InspectionCreate,
    InspectionListResponse,
    InspectionResponse,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/inspections",
    response_model=InspectionListResponse,
)
def get_inspections(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
    page: CollectionPage = Depends(get_collection_page),
):
    inspections = (
        db.query(Inspection)
        .filter(Inspection.project_id == project_id)
        .order_by(Inspection.date.desc(), Inspection.id.desc())
        .offset(page.offset)
        .limit(page.limit)
        .all()
    )

    return {"inspections": inspections}


@router.post(
    "/projects/{project_id}/inspections",
    response_model=InspectionResponse,
    status_code=201,
)
def create_inspection(
    project_id: int,
    inspection: InspectionCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_inspection = Inspection(
        project_id=project_id,
        **inspection.model_dump(),
    )

    db.add(new_inspection)
    db.commit()
    db.refresh(new_inspection)

    return new_inspection
