import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import CostAllocationMethod, GinningCostType, GinningProductType
from app.shared.schemas import AppBaseModel


class GinningProductionCostCreate(AppBaseModel):
    cost_type: GinningCostType
    amount: Decimal = Field(..., gt=0)
    currency: str = "UZS"
    notes: str | None = None


class GinningProductionCostResponse(AppBaseModel):
    id: uuid.UUID
    production_order_id: uuid.UUID
    cost_type: GinningCostType
    amount: Decimal
    currency: str
    notes: str | None
    created_at: datetime


class CostAllocationRequest(AppBaseModel):
    method: CostAllocationMethod
    manual_percentages: dict[uuid.UUID, Decimal] | None = None


class CostAllocationLineResponse(AppBaseModel):
    output_id: uuid.UUID
    product_type: GinningProductType
    quantity_kg: Decimal
    allocated_cost: Decimal
    cost_per_kg: Decimal


class ProductionCostSummaryResponse(AppBaseModel):
    production_order_id: uuid.UUID
    production_number: str
    raw_material_cost: Decimal
    other_costs: list[GinningProductionCostResponse]
    other_costs_total: Decimal
    total_cost: Decimal
    allocation_method: CostAllocationMethod
    allocations: list[CostAllocationLineResponse]


class ProductProfitabilityResponse(AppBaseModel):
    product_type: GinningProductType
    total_sales_value: Decimal
    total_allocated_cost: Decimal
    total_allocated_sales_expenses: Decimal
    profit: Decimal
    total_quantity_sold_kg: Decimal
