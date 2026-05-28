
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.project_company import ProjectCompany
from app.core.security import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_project_owner(project_id: int, user_id: int, db: Session):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project"
        )

    return project


def project_company_to_dict(company):
    return {
        "id": company.id,
        "project_id": company.project_id,
        "name": company.name,
        "trade": company.trade,
    }


@router.get("/projects/{project_id}/companies")
def get_project_companies(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    companies = (
        db.query(ProjectCompany)
        .filter(ProjectCompany.project_id == project_id)
        .order_by(ProjectCompany.name)
        .all()
    )

    return {
        "companies": [
            project_company_to_dict(company)
            for company in companies
        ]
    }


@router.post("/projects/{project_id}/companies")
def create_project_company(
    project_id: int,
    company: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    verify_project_owner(project_id, current_user["id"], db)

    new_company = ProjectCompany(
        project_id=project_id,
        name=company["name"],
        trade=company.get("trade"),
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return project_company_to_dict(new_company)