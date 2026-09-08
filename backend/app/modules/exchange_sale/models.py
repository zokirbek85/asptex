import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import ExchangeSaleStatus, GinningProductType


class ExchangeSale(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "exchange_sales"
    __table_args__ = (
        UniqueConstraint("company_id", "sale_number", name="uq_exchange_sale_company_number"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    sale_number: Mapped[str] = mapped_column(String(30), nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ExchangeSaleStatus] = mapped_column(nullable=False, default=ExchangeSaleStatus.ACTIVE)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )

    exchange_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exchange_lot_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    broker_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    transport_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    other_costs: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNPAID")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    lines: Mapped[list["ExchangeSaleLine"]] = relationship(
        "ExchangeSaleLine", back_populates="sale", cascade="all, delete-orphan",
        order_by="ExchangeSaleLine.line_number", lazy="selectin",
    )
    cancellations: Mapped[list["ExchangeSaleCancellation"]] = relationship(
        "ExchangeSaleCancellation", back_populates="sale", lazy="selectin",
    )


class ExchangeSaleLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "exchange_sale_lines"
    __table_args__ = (
        UniqueConstraint("sale_id", "line_number", name="uq_esl_sale_line"),
        CheckConstraint("quantity_kg > 0", name="chk_esl_qty_positive"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchange_sales.id"), nullable=False, index=True
    )
    product_type: Mapped[GinningProductType] = mapped_column(nullable=False)
    bale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_bales.id"), nullable=True
    )

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    cancelled_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    is_fully_cancelled: Mapped[bool] = mapped_column(nullable=False, default=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sale: Mapped["ExchangeSale"] = relationship("ExchangeSale", back_populates="lines")
    cancellations: Mapped[list["ExchangeSaleCancellation"]] = relationship(
        "ExchangeSaleCancellation", back_populates="sale_line",
    )


class ExchangeSaleCancellation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exchange_sale_cancellations"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_esc_qty_positive"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchange_sales.id"), nullable=False, index=True
    )
    sale_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchange_sale_lines.id"), nullable=True
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reversal_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cancelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sale: Mapped["ExchangeSale"] = relationship("ExchangeSale", back_populates="cancellations")
    sale_line: Mapped["ExchangeSaleLine | None"] = relationship(
        "ExchangeSaleLine", back_populates="cancellations",
    )


class ExchangeSaleNumberSequence(Base):
    __tablename__ = "exchange_sale_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
