import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import GinningProductType, IntercompanyTransferStatus


class IntercompanyTransfer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "intercompany_transfers"

    source_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    destination_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    source_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    destination_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    product_type: Mapped[GinningProductType] = mapped_column(nullable=False)

    transfer_number: Mapped[str] = mapped_column(String(30), nullable=False)
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[IntercompanyTransferStatus] = mapped_column(
        nullable=False, default=IntercompanyTransferStatus.DRAFT
    )

    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_quantity_kg: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    lines: Mapped[list["IntercompanyTransferLine"]] = relationship(
        "IntercompanyTransferLine", back_populates="transfer", cascade="all, delete-orphan", lazy="selectin",
    )


class IntercompanyTransferLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "intercompany_transfer_lines"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_itl_qty_positive"),
    )

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intercompany_transfers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_bales.id"), nullable=True
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    source_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    destination_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    transfer: Mapped["IntercompanyTransfer"] = relationship("IntercompanyTransfer", back_populates="lines")


class IntercompanyTransferNumberSequence(Base):
    __tablename__ = "intercompany_transfer_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
