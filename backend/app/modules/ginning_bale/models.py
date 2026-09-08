import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import GinningBaleStatus


class GinningBale(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individually identifiable fiber bale. A traceability/physical-unit record,
    NOT a stock-ledger dimension — the aggregate FIBER quantity is already posted
    once per production order's output line; bales itemize that same quantity.
    """
    __tablename__ = "ginning_bales"
    __table_args__ = (
        UniqueConstraint("company_id", "bale_number", name="uq_ginning_bale_company_number"),
        CheckConstraint("gross_weight_kg > tare_weight_kg", name="chk_gb_gross_gt_tare"),
        CheckConstraint("net_weight_kg > 0", name="chk_gb_net_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    production_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_production_orders.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )

    bale_number: Mapped[str] = mapped_column(String(30), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    gross_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    tare_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    net_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    moisture_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    micronaire: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    staple_length_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    strength: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trash_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_class: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[GinningBaleStatus] = mapped_column(nullable=False, default=GinningBaleStatus.IN_STOCK)
    sold_reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sold_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class GinningBaleNumberSequence(Base):
    __tablename__ = "ginning_bale_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
