
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_owned_project
from app.models.project import Project
from app.models.project_company import ProjectCompany
from app.schemas.project_company import (
    ProjectCompanyCreate,
    ProjectCompanyListResponse,
    ProjectCompanyResponse,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/companies",
    response_model=ProjectCompanyListResponse,
)
def get_project_companies(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    companies = (
        db.query(ProjectCompany)
        .filter(ProjectCompany.project_id == project_id)
        .order_by(ProjectCompany.name)
        .all()
    )

    return {"companies": companies}


@router.post(
    "/projects/{project_id}/companies",
    response_model=ProjectCompanyResponse,
    status_code=201,
)
def create_project_company(
    project_id: int,
    company: ProjectCompanyCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_owned_project),
):
    new_company = ProjectCompany(
        project_id=project_id,
        **company.model_dump(),
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company
