from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import Field

from app.shared.enums import AdjustmentStatus, PackagingItemType, WasteType
from app.shared.schemas import AppBaseModel


class AdjustmentLineCreate(AppBaseModel):
    lot_id: uuid.UUID | None = None
    count_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    waste_type: WasteType | None = None
    pkg_item_type: PackagingItemType | None = None
    quantity_kg_after: Decimal = Field(..., ge=0)
    bags_after: int = 0
    units_after: int = 0
    notes: str | None = None


class AdjustmentCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    adjustment_date: date
    reason: str = Field(..., min_length=10)
    notes: str | None = None


class AdjustmentLineResponse(AppBaseModel):
    id: uuid.UUID
    line_number: int
    lot_id: uuid.UUID | None
    count_id: uuid.UUID | None
    owner_id: uuid.UUID | None
    waste_type: WasteType | None
    pkg_item_type: PackagingItemType | None
    quantity_kg_before: Decimal
    quantity_kg_after: Decimal
    bags_before: int
    bags_after: int
    units_before: int
    units_after: int
    transaction_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class AdjustmentResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    adjustment_number: str
    adjustment_date: date
    reason: str
    status: AdjustmentStatus
    lines: list[AdjustmentLineResponse] = []
    posted_at: datetime | None
    posted_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
