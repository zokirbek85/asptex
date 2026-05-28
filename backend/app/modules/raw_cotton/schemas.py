from datetime import date
from decimal import Decimal
import uuid

from app.shared.schemas import AppBaseModel


class RawCottonStockItem(AppBaseModel):
    lot_id: uuid.UUID | None
    lot_number: str | None
    count_id: uuid.UUID | None
    count_value: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    quantity_kg: Decimal
    quantity_kip: Decimal | None


class ProductionIssueItem(AppBaseModel):
    lot_id: uuid.UUID | None
    lot_number: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    total_kg: Decimal
    transaction_count: int


class CottonBalanceSummary(AppBaseModel):
    own_kg: Decimal
    tolling_kg: Decimal
    total_kg: Decimal
    own_items: int
    tolling_items: int
