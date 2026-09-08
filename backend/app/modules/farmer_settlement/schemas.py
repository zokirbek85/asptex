import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.shared.enums import FarmerLedgerEntryType, FarmerPaymentStatus
from app.shared.schemas import AppBaseModel


class FarmerPaymentCreate(AppBaseModel):
    farmer_id: uuid.UUID
    payment_date: date
    amount: Decimal = Field(..., gt=0)
    currency: str = "UZS"
    payment_method: str = "CASH"
    reference_note: str | None = None


class FarmerPaymentCancel(AppBaseModel):
    reason: str = Field(..., min_length=5)


class FarmerPaymentResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    farmer_id: uuid.UUID
    farmer_name: str
    payment_number: str
    payment_date: date
    amount: Decimal
    currency: str
    payment_method: str
    status: FarmerPaymentStatus
    posted_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    reference_note: str | None
    created_at: datetime


class FarmerLedgerEntryResponse(AppBaseModel):
    id: uuid.UUID
    entry_type: FarmerLedgerEntryType
    direction: int
    amount: Decimal
    currency: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    entry_date: date
    notes: str | None
    created_at: datetime


class FarmerBalanceResponse(AppBaseModel):
    farmer_id: uuid.UUID
    farmer_name: str
    balance: Decimal
    currency: str = "UZS"
