from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import Field, field_validator

from app.modules.stock.schemas import StockWarning
from app.shared.enums import ShipmentStatus
from app.shared.schemas import AppBaseModel


class ShipmentLineCreate(AppBaseModel):
    lot_id: uuid.UUID
    count_id: uuid.UUID
    owner_id: uuid.UUID
    quantity_kg: Decimal = Field(..., gt=0)
    quantity_bags: int | None = None
    notes: str | None = None


class ShipmentCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    shipment_date: date
    buyer_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    lines: list[ShipmentLineCreate] = Field(..., min_length=1)
    notes: str | None = None


class ShipmentLineCancelRequest(AppBaseModel):
    quantity_kg: Decimal = Field(..., gt=0)
    quantity_bags: int | None = None
    reason: str = Field(..., min_length=5)


class ShipmentLineResponse(AppBaseModel):
    id: uuid.UUID
    line_number: int
    lot_id: uuid.UUID
    lot_number: str
    count_id: uuid.UUID
    count_value: str
    owner_id: uuid.UUID
    owner_name: str
    quantity_kg: Decimal
    quantity_bags: int | None
    cancelled_kg: Decimal
    cancelled_bags: int
    is_fully_cancelled: bool
    net_kg: Decimal


class ShipmentResponse(AppBaseModel):
    id: uuid.UUID
    shipment_number: str
    shipment_date: date
    status: ShipmentStatus
    buyer_id: uuid.UUID
    buyer_name: str
    contract_id: uuid.UUID | None
    warehouse_id: uuid.UUID
    lines: list[ShipmentLineResponse]
    total_kg: Decimal
    net_kg: Decimal
    notes: str | None
    created_at: datetime
    warnings: list[StockWarning] | None = None
