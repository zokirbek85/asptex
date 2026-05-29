from datetime import date, datetime
from decimal import Decimal
import uuid

from app.shared.enums import PackagingItemType, TransactionType
from app.shared.schemas import AppBaseModel


class PkgUnitType(str):
    KG = "kg"
    DONA = "dona"
    KOMPLEKT = "komplekt"


PKG_TYPE_LABELS: dict[PackagingItemType, str] = {
    PackagingItemType.BAG: "Qop (Bag)",
    PackagingItemType.CONE: "Konus (Cone)",
    PackagingItemType.PACKAGE: "Paket",
    PackagingItemType.CORRUGATED_SHEET: "Gofrokarton",
    PackagingItemType.PARAFFIN: "Parafin",
    PackagingItemType.BOX: "Quti (Box)",
}

# Unit type per packaging item: "kg", "dona", or "komplekt"
PKG_UNIT_TYPES: dict[PackagingItemType, str] = {
    PackagingItemType.BAG: PkgUnitType.DONA,
    PackagingItemType.CONE: PkgUnitType.DONA,
    PackagingItemType.PACKAGE: PkgUnitType.KOMPLEKT,
    PackagingItemType.CORRUGATED_SHEET: PkgUnitType.DONA,
    PackagingItemType.PARAFFIN: PkgUnitType.KG,
    PackagingItemType.BOX: PkgUnitType.KOMPLEKT,
}

MIN_STOCK_THRESHOLDS: dict[PackagingItemType, float] = {
    PackagingItemType.BAG: 100,
    PackagingItemType.CONE: 100,
    PackagingItemType.PACKAGE: 10,
    PackagingItemType.CORRUGATED_SHEET: 100,
    PackagingItemType.PARAFFIN: 50,
    PackagingItemType.BOX: 10,
}


class PackagingStockItem(AppBaseModel):
    pkg_item_type: PackagingItemType
    display_name: str
    unit_type: str
    quantity_units: int | None
    quantity_kg: Decimal


class PackagingMovementItem(AppBaseModel):
    id: uuid.UUID
    pkg_item_type: PackagingItemType
    display_name: str
    unit_type: str
    transaction_type: TransactionType
    direction: int
    quantity_kg: Decimal
    quantity_units: int | None
    transaction_date: date
    posted_at: datetime


class MinStockAlert(AppBaseModel):
    pkg_item_type: PackagingItemType
    display_name: str
    unit_type: str
    current_qty: float
    min_qty: float
