from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.common import MutationModel, ORMModel


TemplateName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class TemplateCreate(MutationModel):
    name: TemplateName


class TemplateResponse(ORMModel):
    id: int
    name: str


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
