from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import Field

from app.shared.enums import AdjustmentStatus, PackagingItemType, WasteType
from app.shared.schemas import AppBaseModel


class OpeningBalanceLineCreate(AppBaseModel):
    lot_id: uuid.UUID | None = None
    count_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    waste_type: WasteType | None = None
    pkg_item_type: PackagingItemType | None = None
    quantity_kg: Decimal = Field(..., gt=0)
    quantity_bags: int | None = None
    quantity_kip: Decimal | None = None
    quantity_units: int | None = None
    notes: str | None = None


class OpeningBalanceCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    balance_date: date
    notes: str | None = None


class OpeningBalanceLineResponse(AppBaseModel):
    id: uuid.UUID
    line_number: int
    lot_id: uuid.UUID | None
    count_id: uuid.UUID | None
    owner_id: uuid.UUID | None
    waste_type: WasteType | None
    pkg_item_type: PackagingItemType | None
    quantity_kg: Decimal
    quantity_bags: int | None
    quantity_kip: Decimal | None
    quantity_units: int | None
    lot_number: str | None
    count_value: str | None
    owner_name: str | None
    transaction_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class OpeningBalanceResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    balance_date: date
    status: AdjustmentStatus
    notes: str | None
    lines: list[OpeningBalanceLineResponse] = []
    posted_at: datetime | None
    posted_by: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
