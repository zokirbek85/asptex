from datetime import date, datetime
from decimal import Decimal
import uuid

from app.shared.enums import TransactionType, WasteType
from app.shared.schemas import AppBaseModel

WASTE_TYPE_LABELS: dict[WasteType, str] = {
    WasteType.ST_3: "ST-3",
    WasteType.ST_7_11: "ST-7-11",
    WasteType.ST_1: "ST-1",
    WasteType.ST_36: "ST-36",
    WasteType.ST_98: "ST-98",
    WasteType.MYCHKA: "Mychka",
    WasteType.ROVNITSA: "Rovnitsa",
}


class WasteStockItem(AppBaseModel):
    waste_type: WasteType
    display_name: str
    quantity_kg: Decimal


class WasteMovementItem(AppBaseModel):
    id: uuid.UUID
    waste_type: WasteType
    display_name: str
    transaction_type: TransactionType
    direction: int
    quantity_kg: Decimal
    owner_name: str | None
    transaction_date: date
    posted_at: datetime


class WasteSalesReportItem(AppBaseModel):
    buyer_id: uuid.UUID | None
    buyer_name: str | None
    waste_type: WasteType
    display_name: str
    total_kg: Decimal
    transaction_count: int
