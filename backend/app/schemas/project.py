from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.common import MutationModel, ORMModel


ProjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ProjectCreate(MutationModel):
    name: ProjectName


class ProjectResponse(ORMModel):
    id: int
    name: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
