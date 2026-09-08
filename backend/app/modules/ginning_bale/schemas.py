import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.shared.enums import GinningBaleStatus
from app.shared.schemas import AppBaseModel


class GinningBaleCreate(AppBaseModel):
    production_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    gross_weight_kg: Decimal = Field(..., gt=0)
    tare_weight_kg: Decimal = Field(..., ge=0)
    moisture_pct: Decimal | None = None
    micronaire: Decimal | None = None
    staple_length_mm: Decimal | None = None
    strength: Decimal | None = None
    color: str | None = None
    trash_pct: Decimal | None = None
    grade: str | None = None
    quality_class: str | None = None
    notes: str | None = None

    @field_validator("tare_weight_kg")
    @classmethod
    def tare_less_than_gross(cls, v: Decimal, info) -> Decimal:
        gross = info.data.get("gross_weight_kg")
        if gross is not None and v >= gross:
            raise ValueError("tare_weight_kg must be less than gross_weight_kg")
        return v


class GinningBaleResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    production_order_id: uuid.UUID
    production_number: str
    warehouse_id: uuid.UUID
    bale_number: str
    production_date: date
    gross_weight_kg: Decimal
    tare_weight_kg: Decimal
    net_weight_kg: Decimal
    moisture_pct: Decimal | None
    micronaire: Decimal | None
    staple_length_mm: Decimal | None
    strength: Decimal | None
    color: str | None
    trash_pct: Decimal | None
    grade: str | None
    quality_class: str | None
    status: GinningBaleStatus
    notes: str | None
    created_at: datetime


class GinningBaleCreateResult(AppBaseModel):
    bale: GinningBaleResponse
    reconciliation_warning: str | None = None
