from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import Field

from app.shared.enums import LineCategory, PackagingItemType, ReportStatus, WasteType
from app.shared.schemas import AppBaseModel


class DailyReportLineCreate(AppBaseModel):
    line_category: LineCategory
    lot_id: uuid.UUID | None = None
    count_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    waste_type: WasteType | None = None
    buyer_id: uuid.UUID | None = None
    pkg_item_type: PackagingItemType | None = None
    quantity_kg: Decimal = Decimal("0")
    quantity_bags: int | None = None
    quantity_kip: Decimal | None = None
    quantity_units: int | None = None
    notes: str | None = None


class DailyReportLineResponse(DailyReportLineCreate):
    id: uuid.UUID
    line_number: int
    transaction_id: uuid.UUID | None = None


class OpeningBalanceLine(AppBaseModel):
    lot_id: uuid.UUID | None = None
    lot_number: str | None = None
    count_id: uuid.UUID | None = None
    count_value: str | None = None
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    waste_type: WasteType | None = None
    pkg_item_type: PackagingItemType | None = None
    quantity_kg: Decimal
    quantity_bags: int | None = None
    quantity_units: int | None = None


class DailyReportCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    report_date: date
    notes: str | None = None


class DailyReportSubmit(AppBaseModel):
    lines: list[DailyReportLineCreate]


class DailyReportReopen(AppBaseModel):
    reopen_reason: str = Field(..., min_length=10)


class TollingWarning(AppBaseModel):
    tolling_lot_id: str
    dist_exists: bool
    dist_confirmed: bool = False
    distribution_id: str | None = None
    warning: str


class DailyReportResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    report_date: date
    status: ReportStatus
    opening_balance: list[OpeningBalanceLine] = []
    lines: list[DailyReportLineResponse] = []
    submitted_at: datetime | None = None
    submitted_by: uuid.UUID | None = None
    closed_at: datetime | None = None
    closed_by: uuid.UUID | None = None
    reopen_count: int = 0
    notes: str | None = None
    created_at: datetime
    tolling_warnings: list[TollingWarning] | None = None


# ── Running Balance ──────────────────────────────────────────────────────────

class OwnerBalanceLine(AppBaseModel):
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    quantity_kg: float
    quantity_bags: int | None = None
    is_tolling: bool = False


class LotBalanceSummary(AppBaseModel):
    lot_id: uuid.UUID | None = None
    lot_number: str | None = None
    count_id: uuid.UUID | None = None
    count_value: str | None = None
    total_kg: float
    own_kg: float
    tolling_kg: float
    by_owner: list[OwnerBalanceLine]


class TollingParticipantBalance(AppBaseModel):
    counterparty_id: uuid.UUID
    counterparty_name: str
    raw_kg_contract: float
    raw_kg_actual: float
    raw_kg_diff: float
    fg_gross_kg: float
    fg_fee_kg: float
    fg_net_kg: float
    fg_stock_kg: float
    fg_shipped_kg: float


class TollingBalanceSummary(AppBaseModel):
    tolling_lot_id: uuid.UUID
    lot_number: str
    status: str
    participants: list[TollingParticipantBalance]


class WarehouseRunningBalance(AppBaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    as_of_date: date
    lots: list[LotBalanceSummary]
    total_kg: float
    total_own_kg: float
    total_tolling_kg: float
    tolling_lots: list[TollingBalanceSummary] = []
