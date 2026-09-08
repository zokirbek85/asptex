import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import CottonReceivingStatus


class CottonReceiving(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cotton_receiving"
    __table_args__ = (
        UniqueConstraint("company_id", "receiving_number", name="uq_cotton_receiving_company_number"),
        CheckConstraint("gross_weight_kg > tare_weight_kg", name="chk_cr_gross_gt_tare"),
        CheckConstraint("net_weight_kg > 0", name="chk_cr_net_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    bunt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_bunts.id"), nullable=False, index=True
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )

    receiving_number: Mapped[str] = mapped_column(String(30), nullable=False)
    receiving_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    vehicle_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    gross_weight_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    tare_weight_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    net_weight_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)

    moisture_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    contamination_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    variety: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_class: Mapped[str | None] = mapped_column(String(20), nullable=True)

    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_source: Mapped[str | None] = mapped_column(String(20), nullable=True)  # MANUAL | PRICE_LIST
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")

    status: Mapped[CottonReceivingStatus] = mapped_column(nullable=False, default=CottonReceivingStatus.DRAFT)

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Denormalized snapshots (frozen at creation, for reporting)
    farmer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CottonReceivingNumberSequence(Base):
    """SELECT FOR UPDATE sequence for cotton receiving number generation."""
    __tablename__ = "cotton_receiving_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class CottonPriceList(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Transparent quality-based price lookup: grade/variety/sort/quality_class -> price/kg.
    NULL in any dimension acts as a wildcard for that dimension.
    """
    __tablename__ = "cotton_price_list"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    variety: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_class: Mapped[str | None] = mapped_column(String(20), nullable=True)

    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
