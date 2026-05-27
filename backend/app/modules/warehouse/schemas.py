import uuid
from datetime import datetime

from pydantic import Field

from app.shared.enums import WarehouseType
from app.shared.schemas import AppBaseModel


class WarehouseCreate(AppBaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=255)
    warehouse_type: WarehouseType
    description: str | None = None
    sort_order: int = Field(0, ge=0, le=9999)


class WarehouseUpdate(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = Field(None, ge=0, le=9999)


class WarehouseResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    warehouse_type: WarehouseType
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
