from datetime import date
from decimal import Decimal

from app.shared.schemas import AppBaseModel


class GinningDashboardSummary(AppBaseModel):
    raw_cotton_received_kg: Decimal
    raw_cotton_available_kg: Decimal
    raw_cotton_processed_kg: Decimal
    fiber_produced_kg: Decimal
    seed_produced_kg: Decimal
    lint_produced_kg: Decimal
    pux_produced_kg: Decimal
    ulyuk_produced_kg: Decimal
    total_output_kg: Decimal
    fiber_yield_pct: Decimal
    exchange_sales_value: Decimal
    exchange_sales_kg: Decimal
    intercompany_transfers_kg: Decimal
    farmer_payable_total: Decimal
    farmer_paid_total: Decimal
    open_bunts_count: int
    draft_production_orders_count: int


class ChartDataPoint(AppBaseModel):
    label: str
    value: Decimal


class GinningReceivingTrendPoint(AppBaseModel):
    date: date
    quantity_kg: Decimal
