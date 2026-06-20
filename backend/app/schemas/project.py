from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectResponse(ORMModel):
    id: int
    name: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
