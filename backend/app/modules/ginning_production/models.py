import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import GinningProductionStatus, GinningProductType


class GinningProductionOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ginning_production_orders"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    production_number: Mapped[str] = mapped_column(String(30), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[GinningProductionStatus] = mapped_column(
        nullable=False, default=GinningProductionStatus.DRAFT
    )

    total_input_kg: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    total_output_kg: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    inputs: Mapped[list["GinningProductionInput"]] = relationship(
        "GinningProductionInput", back_populates="order", cascade="all, delete-orphan", lazy="selectin",
    )
    outputs: Mapped[list["GinningProductionOutput"]] = relationship(
        "GinningProductionOutput", back_populates="order", cascade="all, delete-orphan", lazy="selectin",
    )


class GinningProductionInput(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ginning_production_inputs"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_gpi_qty_positive"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_production_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bunt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_bunts.id"), nullable=False
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    order: Mapped["GinningProductionOrder"] = relationship("GinningProductionOrder", back_populates="inputs")


class GinningProductionOutput(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ginning_production_outputs"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_gpo_qty_positive"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_production_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_type: Mapped[GinningProductType] = mapped_column(nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["GinningProductionOrder"] = relationship("GinningProductionOrder", back_populates="outputs")


class GinningProductionNumberSequence(Base):
    __tablename__ = "ginning_production_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
