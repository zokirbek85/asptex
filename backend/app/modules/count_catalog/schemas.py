import uuid
from datetime import datetime

from pydantic import Field

from app.shared.schemas import AppBaseModel


class CountCreate(AppBaseModel):
    count_value: str = Field(..., min_length=1, max_length=50)
    yarn_type: str | None = Field(None, max_length=100)
    composition: str | None = None
    description: str | None = None


class CountUpdate(AppBaseModel):
    yarn_type: str | None = Field(None, max_length=100)
    composition: str | None = None
    description: str | None = None


class CountResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    count_value: str
    yarn_type: str | None
    composition: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
