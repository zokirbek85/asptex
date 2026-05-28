from datetime import date
from decimal import Decimal
import uuid

from app.shared.enums import LotStatus, WarehouseType
from app.shared.schemas import AppBaseModel


class DashboardSummary(AppBaseModel):
    finished_goods_kg: Decimal
    raw_cotton_kg: Decimal
    waste_kg: Decimal
    packaging_units: int

    shipments_this_month: int
    shipments_kg_this_month: Decimal

    active_lots: int
    open_daily_reports: int

    slow_stock_count: int
    pending_adjustments: int


class ChartDataPoint(AppBaseModel):
    date: date
    value: Decimal
    label: str | None = None


class StockByLot(AppBaseModel):
    lot_id: uuid.UUID
    lot_number: str
    status: LotStatus
    total_kg: Decimal
    total_bags: int
    owners: int


class SlowStockItem(AppBaseModel):
    warehouse_type: WarehouseType
    identifier: str
    quantity_kg: Decimal
    last_movement_date: date | None
    days_idle: int


class DashboardAlert(AppBaseModel):
    alert_type: str
    severity: str
    message: str
    reference_id: uuid.UUID | None = None
