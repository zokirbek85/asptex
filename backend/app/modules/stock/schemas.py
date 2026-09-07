import uuid
from decimal import Decimal

from app.shared.schemas import AppBaseModel


class StockWarning(AppBaseModel):
    """Surfaced to the API caller when a posting would drive a balance negative
    but is not hard-blocked (see StockService.check_balance_and_warn)."""

    warehouse_id: uuid.UUID
    lot_number: str | None = None
    count_value: str | None = None
    owner_name: str | None = None
    current_kg: Decimal
    after_kg: Decimal
