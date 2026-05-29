import uuid
from datetime import datetime

from pydantic import Field

from app.shared.enums import LotStatus
from app.shared.schemas import AppBaseModel


class LotCreate(AppBaseModel):
    notes: str | None = None


class LotUpdate(AppBaseModel):
    notes: str | None = None


class LotClose(AppBaseModel):
    reason: str | None = Field(None, max_length=500)


class LotReopen(AppBaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class StockSummaryItem(AppBaseModel):
    count_id: uuid.UUID
    count_value: str
    owner_id: uuid.UUID | None
    owner_name: str | None
    total_kg: float
    warehouse_id: uuid.UUID
    warehouse_name: str


class LotResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    lot_number: str
    year: int
    sequence_number: int
    status: LotStatus
    opened_at: datetime
    closed_at: datetime | None
    closed_by: uuid.UUID | None
    close_reason: str | None
    auto_closed: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    stock_summary: list[StockSummaryItem] = []
    tolling_lot_id: uuid.UUID | None = None
