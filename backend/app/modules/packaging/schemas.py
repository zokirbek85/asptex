from datetime import date, datetime
from decimal import Decimal
import uuid

from app.shared.enums import PackagingItemType, TransactionType
from app.shared.schemas import AppBaseModel

PKG_TYPE_LABELS: dict[PackagingItemType, str] = {
    PackagingItemType.BAG: "Qop (Bag)",
    PackagingItemType.CONE: "Konus (Cone)",
    PackagingItemType.PACKAGE: "Paket",
    PackagingItemType.CORRUGATED_SHEET: "Gofrokarton",
    PackagingItemType.PARAFFIN: "Parafin",
    PackagingItemType.BOX: "Quti (Box)",
}

MIN_STOCK_THRESHOLDS: dict[PackagingItemType, int] = {
    PackagingItemType.BAG: 100,
    PackagingItemType.CONE: 100,
    PackagingItemType.PACKAGE: 100,
    PackagingItemType.CORRUGATED_SHEET: 100,
    PackagingItemType.PARAFFIN: 100,
    PackagingItemType.BOX: 100,
}


class PackagingStockItem(AppBaseModel):
    pkg_item_type: PackagingItemType
    display_name: str
    quantity_units: int | None
    quantity_kg: Decimal


class PackagingMovementItem(AppBaseModel):
    id: uuid.UUID
    pkg_item_type: PackagingItemType
    display_name: str
    transaction_type: TransactionType
    direction: int
    quantity_kg: Decimal
    quantity_units: int | None
    transaction_date: date
    posted_at: datetime


class MinStockAlert(AppBaseModel):
    pkg_item_type: PackagingItemType
    display_name: str
    current_units: int
    min_units: int
