import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import ExchangeSaleStatus, GinningProductType
from app.shared.schemas import AppBaseModel


class ExchangeSaleLineCreate(AppBaseModel):
    product_type: GinningProductType
    bale_id: uuid.UUID | None = None
    quantity_kg: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    currency: str = "UZS"
    notes: str | None = None


class ExchangeSaleCreate(AppBaseModel):
    warehouse_id: uuid.UUID
    sale_date: date
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    exchange_name: str | None = None
    exchange_lot_number: str | None = None
    commission_amount: Decimal | None = None
    broker_name: str | None = None
    transport_cost: Decimal | None = None
    other_costs: Decimal | None = None
    notes: str | None = None
    lines: list[ExchangeSaleLineCreate] = Field(..., min_length=1)


class ExchangeSaleLineCancelRequest(AppBaseModel):
    quantity_kg: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=5)


class ExchangeSaleLineResponse(AppBaseModel):
    id: uuid.UUID
    line_number: int
    product_type: GinningProductType
    bale_id: uuid.UUID | None
    bale_number: str | None
    quantity_kg: Decimal
    unit_price: Decimal
    currency: str
    total_amount: Decimal
    cancelled_kg: Decimal
    is_fully_cancelled: bool
    net_kg: Decimal
    notes: str | None


class ExchangeSaleResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    sale_number: str
    sale_date: date
    status: ExchangeSaleStatus
    customer_id: uuid.UUID
    customer_name: str
    contract_id: uuid.UUID | None
    exchange_name: str | None
    exchange_lot_number: str | None
    commission_amount: Decimal | None
    broker_name: str | None
    transport_cost: Decimal | None
    other_costs: Decimal | None
    payment_status: str
    lines: list[ExchangeSaleLineResponse]
    total_kg: Decimal
    net_kg: Decimal
    total_value: Decimal
    notes: str | None
    created_at: datetime
