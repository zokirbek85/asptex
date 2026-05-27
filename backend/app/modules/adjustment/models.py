import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from app.shared.enums import AdjustmentStatus, PackagingItemType, WasteType


class InventoryAdjustment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        UniqueConstraint("company_id", "adjustment_number", name="uq_adj_company_number"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    adjustment_number: Mapped[str] = mapped_column(String(20), nullable=False)
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AdjustmentStatus] = mapped_column(nullable=False, default=AdjustmentStatus.DRAFT)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Relationships
    lines: Mapped[list["InventoryAdjustmentLine"]] = relationship(
        "InventoryAdjustmentLine", back_populates="adjustment", cascade="all, delete-orphan",
        order_by="InventoryAdjustmentLine.line_number",
    )


class InventoryAdjustmentLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inventory_adjustment_lines"
    __table_args__ = (
        UniqueConstraint("adjustment_id", "line_number", name="uq_adj_line"),
    )

    adjustment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_adjustments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True
    )
    count_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("count_catalog.id"), nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True
    )
    waste_type: Mapped[WasteType | None] = mapped_column(nullable=True)
    pkg_item_type: Mapped[PackagingItemType | None] = mapped_column(nullable=True)

    quantity_kg_before: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    quantity_kg_after: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    bags_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bags_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    units_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    units_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    adjustment: Mapped["InventoryAdjustment"] = relationship(
        "InventoryAdjustment", back_populates="lines"
    )


class AdjustmentNumberSequence(Base):
    __tablename__ = "adjustment_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
