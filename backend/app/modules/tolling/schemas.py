from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import Field, field_validator

from app.shared.enums import TollingDistributionStatus, TollingLineType, TollingLotStatus
from app.shared.schemas import AppBaseModel


# ── Participants ──────────────────────────────────────────────────────────────

class ParticipantAdd(AppBaseModel):
    counterparty_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    raw_kg_delivered: Decimal = Decimal("0")
    fee_pct: Decimal = Field(..., ge=0, le=100)
    fee_currency: str = "UZS"
    fee_rate_per_kg: Decimal | None = None


class ParticipantUpdate(AppBaseModel):
    fee_pct: Decimal | None = Field(None, ge=0, le=100)
    fee_rate_per_kg: Decimal | None = None
    raw_kg_delivered: Decimal | None = None
    is_active: bool | None = None


class ParticipantOut(AppBaseModel):
    id: uuid.UUID
    tolling_lot_id: uuid.UUID
    counterparty_id: uuid.UUID
    counterparty_name: str | None = None
    contract_id: uuid.UUID | None
    raw_kg_delivered: Decimal
    fee_pct: Decimal
    fee_currency: str
    fee_rate_per_kg: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Tolling Lots ──────────────────────────────────────────────────────────────

class TollingLotCreate(AppBaseModel):
    notes: str | None = None


class TollingLotClose(AppBaseModel):
    close_reason: str | None = None


class TollingLotOut(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    lot_id: uuid.UUID
    lot_number: str | None = None
    status: TollingLotStatus
    opened_at: datetime
    closed_at: datetime | None
    closed_by: uuid.UUID | None
    close_reason: str | None
    notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantOut] = []
    # Running totals
    total_raw_kg: Decimal = Decimal("0")
    total_distributions: int = 0
    total_fg_distributed_kg: Decimal = Decimal("0")


# ── Distributions ─────────────────────────────────────────────────────────────

class RawIntakeItem(AppBaseModel):
    participant_id: uuid.UUID
    raw_kg_received_today: Decimal = Decimal("0")


class RawIntakeItemOut(AppBaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    counterparty_id: uuid.UUID | None = None
    counterparty_name: str | None = None
    raw_kg_received_today: Decimal


class DistributionCreate(AppBaseModel):
    tolling_lot_id: uuid.UUID
    distribution_date: date
    daily_fg_kg_total: Decimal = Field(..., gt=0)
    raw_intakes: list[RawIntakeItem] = []
    notes: str | None = None


class DistributionUpdate(AppBaseModel):
    daily_fg_kg_total: Decimal | None = Field(None, gt=0)
    raw_intakes: list[RawIntakeItem] | None = None
    notes: str | None = None


class DistributionLineOut(AppBaseModel):
    id: uuid.UUID | None = None
    participant_id: uuid.UUID | None
    counterparty_id: uuid.UUID | None
    counterparty_name: str | None
    line_type: TollingLineType
    gross_kg: Decimal
    fee_kg: Decimal
    net_kg: Decimal
    ownership_share_pct: Decimal
    fee_pct_applied: Decimal
    fee_amount_uzs: Decimal | None = None
    fee_amount_usd: Decimal | None = None
    stock_transaction_id: uuid.UUID | None = None


class DistributionOut(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    tolling_lot_id: uuid.UUID
    distribution_date: date
    daily_fg_kg_total: Decimal
    status: TollingDistributionStatus
    confirmed_at: datetime | None
    confirmed_by: uuid.UUID | None
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    lines: list[DistributionLineOut] = []
    raw_intakes: list[RawIntakeItemOut] = []
    total_net_kg: Decimal = Decimal("0")
    total_fee_kg: Decimal = Decimal("0")
    total_kg_check: Decimal = Decimal("0")


# ── Reports ───────────────────────────────────────────────────────────────────

class LotSummaryParticipantRow(AppBaseModel):
    counterparty_id: uuid.UUID
    counterparty_name: str
    raw_kg_delivered: Decimal
    ownership_share_pct: Decimal
    total_gross_kg: Decimal
    total_fee_kg: Decimal
    total_net_kg: Decimal
    fee_amount_uzs: Decimal | None
    fee_amount_usd: Decimal | None


class LotSummaryOut(AppBaseModel):
    tolling_lot_id: uuid.UUID
    lot_number: str
    status: TollingLotStatus
    opened_at: datetime
    closed_at: datetime | None
    rows: list[LotSummaryParticipantRow]
    total_fg_kg: Decimal
    total_fee_kg: Decimal
    total_net_kg: Decimal


class DailyRegisterRow(AppBaseModel):
    distribution_id: uuid.UUID
    distribution_date: date
    daily_fg_kg_total: Decimal
    status: TollingDistributionStatus
    lines: list[DistributionLineOut]
    total_fee_kg: Decimal
    total_net_kg: Decimal


class DailyRegisterOut(AppBaseModel):
    tolling_lot_id: uuid.UUID | None
    date_from: date | None
    date_to: date | None
    rows: list[DailyRegisterRow]
