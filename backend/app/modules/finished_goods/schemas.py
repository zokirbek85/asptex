from datetime import date
from decimal import Decimal
import uuid

from app.shared.enums import LotStatus, TransactionType
from app.shared.schemas import AppBaseModel


class FinishedGoodsStockItem(AppBaseModel):
    lot_id: uuid.UUID
    lot_number: str
    lot_status: LotStatus
    count_id: uuid.UUID | None
    count_value: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    quantity_kg: Decimal
    quantity_bags: int | None


class LotStockBreakdown(AppBaseModel):
    lot_id: uuid.UUID
    lot_number: str
    lot_status: LotStatus
    items: list[FinishedGoodsStockItem]
    total_kg: Decimal


class ProductionReportItem(AppBaseModel):
    lot_id: uuid.UUID
    lot_number: str
    count_id: uuid.UUID | None
    count_value: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    total_kg: Decimal
    transaction_count: int


class ShipmentReportItem(AppBaseModel):
    buyer_id: uuid.UUID | None
    buyer_name: str | None
    lot_id: uuid.UUID
    lot_number: str
    count_id: uuid.UUID | None
    count_value: str | None
    total_kg: Decimal
    transaction_count: int
