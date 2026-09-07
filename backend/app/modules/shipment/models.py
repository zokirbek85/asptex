import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import ShipmentStatus


class Shipment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("company_id", "shipment_number", name="uq_shipment_company_number"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    shipment_number: Mapped[str] = mapped_column(String(25), nullable=False)
    shipment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ShipmentStatus] = mapped_column(nullable=False, default=ShipmentStatus.ACTIVE)

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    daily_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_reports.id"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Relationships
    lines: Mapped[list["ShipmentLine"]] = relationship(
        "ShipmentLine", back_populates="shipment", cascade="all, delete-orphan",
        order_by="ShipmentLine.line_number",
    )
    cancellations: Mapped[list["ShipmentCancellation"]] = relationship(
        "ShipmentCancellation", back_populates="shipment"
    )
    contract: Mapped["Contract | None"] = relationship(  # type: ignore[name-defined]
        "Contract", back_populates="shipments"
    )


class ShipmentLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shipment_lines"
    __table_args__ = (
        UniqueConstraint("shipment_id", "line_number", name="uq_sl_shipment_line"),
        CheckConstraint("quantity_kg > 0", name="chk_sl_qty_positive"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False
    )
    count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("count_catalog.id"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False
    )

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_bags: Mapped[int | None] = mapped_column(nullable=True)

    # Cancellation tracking
    cancelled_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    cancelled_bags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_fully_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="lines")
    cancellations: Mapped[list["ShipmentCancellation"]] = relationship(
        "ShipmentCancellation", back_populates="shipment_line"
    )


class ShipmentCancellation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "shipment_cancellations"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_sc_qty_positive"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False, index=True
    )
    shipment_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipment_lines.id"), nullable=True
    )

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_bags: Mapped[int | None] = mapped_column(nullable=True)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reversal_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    cancelled_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cancelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="cancellations")
    shipment_line: Mapped["ShipmentLine | None"] = relationship(
        "ShipmentLine", back_populates="cancellations"
    )


class ShipmentNumberSequence(Base):
    """SELECT FOR UPDATE sequence for shipment number generation."""
    __tablename__ = "shipment_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year_month: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMM
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
