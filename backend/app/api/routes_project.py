
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.project import Project
from app.core.security import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/projects")
def get_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user["id"])
        .order_by(Project.id)
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


@router.post("/projects")
def create_project(
    project: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    new_project = Project(
        name=project["name"],
        user_id=current_user["id"],
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "id": new_project.id,
        "name": new_project.name,
    }