import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import GinningProductType, IntercompanyTransferStatus
from app.shared.schemas import AppBaseModel


class IntercompanyTransferLineCreate(AppBaseModel):
    bale_id: uuid.UUID | None = None
    quantity_kg: Decimal = Field(..., gt=0)


class IntercompanyTransferCreate(AppBaseModel):
    destination_company_id: uuid.UUID
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    product_type: GinningProductType
    transfer_date: date
    unit_price: Decimal | None = Field(None, gt=0)
    currency: str = "UZS"
    notes: str | None = None
    lines: list[IntercompanyTransferLineCreate] = Field(..., min_length=1)


class IntercompanyTransferCancel(AppBaseModel):
    reason: str = Field(..., min_length=5)


class IntercompanyTransferLineResponse(AppBaseModel):
    id: uuid.UUID
    bale_id: uuid.UUID | None
    bale_number: str | None
    quantity_kg: Decimal


class IntercompanyTransferResponse(AppBaseModel):
    id: uuid.UUID
    source_company_id: uuid.UUID
    source_company_name: str
    destination_company_id: uuid.UUID
    destination_company_name: str
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    product_type: GinningProductType
    transfer_number: str
    transfer_date: date
    status: IntercompanyTransferStatus
    unit_price: Decimal | None
    currency: str
    total_value: Decimal | None
    total_quantity_kg: Decimal
    lines: list[IntercompanyTransferLineResponse]
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    notes: str | None
    created_at: datetime
