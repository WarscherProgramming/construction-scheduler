
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.project import Project

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/projects")
def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()

    return {
        "projects": [
            {
                "id": project.id,
                "name": project.name
            }
            for project in projects
        ]
    }


@router.post("/projects")
def create_project(project: dict, db: Session = Depends(get_db)):
    new_project = Project(
        name=project["name"]
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "id": new_project.id,
        "name": new_project.name
    }