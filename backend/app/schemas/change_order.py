from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.task import DateString


class ChangeOrderCreate(BaseModel):
    date: DateString
    co_number: str = Field(min_length=1, max_length=100)
    company: str | None = Field(default=None, max_length=255)
    status: str = Field(min_length=1, max_length=100)
    description: str | None = None
    amount: str | None = Field(default=None, max_length=100)
    responsible_party: str | None = Field(default=None, max_length=255)


class ChangeOrderResponse(ORMModel):
    id: int
    project_id: int
    date: str
    co_number: str
    company: str | None
    status: str
    description: str | None
    amount: str | None
    responsible_party: str | None


class ChangeOrderListResponse(BaseModel):
    change_orders: list[ChangeOrderResponse]
