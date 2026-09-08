import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.shared.enums import CottonReceivingStatus
from app.shared.schemas import AppBaseModel


class CottonReceivingCreate(AppBaseModel):
    bunt_id: uuid.UUID
    farmer_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    receiving_date: date
    vehicle_number: str | None = None
    driver_name: str | None = None
    gross_weight_kg: Decimal = Field(..., gt=0)
    tare_weight_kg: Decimal = Field(..., ge=0)
    moisture_pct: Decimal | None = None
    contamination_pct: Decimal | None = None
    grade: str | None = None
    variety: str | None = None
    sort: str | None = None
    quality_class: str | None = None
    unit_price: Decimal | None = Field(None, gt=0)
    currency: str = "UZS"
    notes: str | None = None

    @field_validator("tare_weight_kg")
    @classmethod
    def tare_less_than_gross(cls, v: Decimal, info) -> Decimal:
        gross = info.data.get("gross_weight_kg")
        if gross is not None and v >= gross:
            raise ValueError("tare_weight_kg must be less than gross_weight_kg")
        return v


class CottonReceivingUpdate(AppBaseModel):
    contract_id: uuid.UUID | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    gross_weight_kg: Decimal | None = Field(None, gt=0)
    tare_weight_kg: Decimal | None = Field(None, ge=0)
    moisture_pct: Decimal | None = None
    contamination_pct: Decimal | None = None
    grade: str | None = None
    variety: str | None = None
    sort: str | None = None
    quality_class: str | None = None
    unit_price: Decimal | None = Field(None, gt=0)
    notes: str | None = None


class CottonReceivingCancel(AppBaseModel):
    reason: str = Field(..., min_length=5)


class CottonReceivingResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    bunt_id: uuid.UUID
    bunt_lot_number: str
    farmer_id: uuid.UUID
    farmer_name: str
    contract_id: uuid.UUID | None
    receiving_number: str
    receiving_date: date
    vehicle_number: str | None
    driver_name: str | None
    gross_weight_kg: Decimal
    tare_weight_kg: Decimal
    net_weight_kg: Decimal
    moisture_pct: Decimal | None
    contamination_pct: Decimal | None
    grade: str | None
    variety: str | None
    sort: str | None
    quality_class: str | None
    unit_price: Decimal | None
    price_source: str | None
    total_amount: Decimal | None
    currency: str
    status: CottonReceivingStatus
    posted_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    notes: str | None
    created_at: datetime


class CottonPriceListCreate(AppBaseModel):
    grade: str | None = None
    variety: str | None = None
    sort: str | None = None
    quality_class: str | None = None
    price_per_kg: Decimal = Field(..., gt=0)
    currency: str = "UZS"
    effective_from: date


class CottonPriceListResponse(AppBaseModel):
    id: uuid.UUID
    grade: str | None
    variety: str | None
    sort: str | None
    quality_class: str | None
    price_per_kg: Decimal
    currency: str
    effective_from: date
    is_active: bool
    created_at: datetime
