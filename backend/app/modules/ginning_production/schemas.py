import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import GinningProductionStatus, GinningProductType
from app.shared.schemas import AppBaseModel


class GinningProductionInputCreate(AppBaseModel):
    bunt_id: uuid.UUID
    quantity_kg: Decimal = Field(..., gt=0)


class GinningProductionOutputCreate(AppBaseModel):
    product_type: GinningProductType
    warehouse_id: uuid.UUID
    quantity_kg: Decimal = Field(..., gt=0)
    notes: str | None = None


class GinningProductionOrderCreate(AppBaseModel):
    production_date: date
    notes: str | None = None
    inputs: list[GinningProductionInputCreate] = Field(..., min_length=1)
    outputs: list[GinningProductionOutputCreate] = Field(..., min_length=1)


class GinningProductionOrderUpdate(AppBaseModel):
    notes: str | None = None
    inputs: list[GinningProductionInputCreate] = Field(..., min_length=1)
    outputs: list[GinningProductionOutputCreate] = Field(..., min_length=1)


class GinningProductionCancel(AppBaseModel):
    reason: str = Field(..., min_length=5)


class GinningProductionInputResponse(AppBaseModel):
    id: uuid.UUID
    bunt_id: uuid.UUID
    bunt_lot_number: str
    quantity_kg: Decimal


class GinningProductionOutputResponse(AppBaseModel):
    id: uuid.UUID
    product_type: GinningProductType
    warehouse_id: uuid.UUID
    warehouse_name: str
    quantity_kg: Decimal
    yield_pct: Decimal | None
    notes: str | None


class GinningProductionOrderResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    production_number: str
    production_date: date
    status: GinningProductionStatus
    inputs: list[GinningProductionInputResponse]
    outputs: list[GinningProductionOutputResponse]
    total_input_kg: Decimal
    total_output_kg: Decimal
    diff_kg: Decimal
    yield_pct: Decimal
    loss_pct: Decimal
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    notes: str | None
    created_at: datetime
