from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TemplateResponse(ORMModel):
    id: int
    name: str


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
