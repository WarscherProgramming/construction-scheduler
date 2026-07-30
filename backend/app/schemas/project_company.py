from pydantic import BaseModel, Field

from app.schemas.common import MutationModel, ORMModel


class ProjectCompanyCreate(MutationModel):
    name: str = Field(min_length=1, max_length=255)
    trade: str | None = Field(default=None, max_length=255)


class ProjectCompanyResponse(ORMModel):
    id: int
    project_id: int
    name: str
    trade: str | None


class ProjectCompanyListResponse(BaseModel):
    companies: list[ProjectCompanyResponse]
