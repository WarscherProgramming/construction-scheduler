
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import CollectionPage, get_collection_page, get_db
from app.models.project import Project
from app.core.security import get_current_user
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse

router = APIRouter()


@router.get("/projects", response_model=ProjectListResponse)
def get_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: CollectionPage = Depends(get_collection_page),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user["id"])
        .order_by(Project.id)
        .offset(page.offset)
        .limit(page.limit)
        .all()
    )

    return {
        "projects": [
            {
                "id": project.id,
                "name": project.name,
            }
            for project in projects
        ]
    }


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    new_project = Project(
        name=project.name,
        user_id=current_user["id"],
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "id": new_project.id,
        "name": new_project.name,
    }
