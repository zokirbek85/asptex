import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from app.shared.enums import AdjustmentStatus, PackagingItemType, WasteType


class OpeningBalanceEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opening_balance_entries"
    __table_args__ = (
        UniqueConstraint("company_id", "warehouse_id", "balance_date", name="uq_ob_company_warehouse_date"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    balance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AdjustmentStatus] = mapped_column(nullable=False, default=AdjustmentStatus.DRAFT)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    lines: Mapped[list["OpeningBalanceLine"]] = relationship(
        "OpeningBalanceLine", back_populates="entry", cascade="all, delete-orphan",
        order_by="OpeningBalanceLine.line_number",
    )


class OpeningBalanceLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "opening_balance_lines"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opening_balance_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True)
    count_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("count_catalog.id"), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True)
    waste_type: Mapped[WasteType | None] = mapped_column(nullable=True)
    pkg_item_type: Mapped[PackagingItemType | None] = mapped_column(nullable=True)

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_bags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_kip: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    quantity_units: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalized snapshots (filled on post)
    lot_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    count_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    entry: Mapped["OpeningBalanceEntry"] = relationship("OpeningBalanceEntry", back_populates="lines")
