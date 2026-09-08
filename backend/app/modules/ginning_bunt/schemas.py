import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import BuntStatus
from app.shared.schemas import AppBaseModel


class GinningBuntCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    notes: str | None = None


class GinningBuntClose(AppBaseModel):
    reason: str | None = None


class BuntFarmerComposition(AppBaseModel):
    farmer_id: uuid.UUID
    farmer_name: str
    total_net_kg: Decimal
    receiving_count: int


class GinningBuntResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    lot_id: uuid.UUID
    lot_number: str
    warehouse_id: uuid.UUID
    status: BuntStatus
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None
    notes: str | None
    created_at: datetime


class GinningBuntDetailResponse(GinningBuntResponse):
    balance_kg: Decimal
    composition: list[BuntFarmerComposition] = Field(default_factory=list)
