import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, UUIDPrimaryKeyMixin
from app.shared.enums import GinningProductType, PackagingItemType, TransactionType, WasteType


class StockTransaction(Base, UUIDPrimaryKeyMixin):
    """
    Append-only ledger. NEVER update or delete rows.
    Stock = SUM(quantity_kg * direction) grouped by identity dimensions.
    """
    __tablename__ = "stock_transactions"
    __table_args__ = (
        CheckConstraint("direction IN (1, -1)", name="chk_direction"),
        CheckConstraint("quantity_kg > 0", name="chk_qty_positive"),
        Index("idx_st_balance_key", "company_id", "warehouse_id", "lot_id", "count_id", "owner_id"),
        Index("idx_st_waste_balance", "company_id", "warehouse_id", "waste_type"),
        Index("idx_st_pkg_balance", "company_id", "warehouse_id", "pkg_item_type"),
        Index("idx_st_ginning_balance", "company_id", "warehouse_id", "ginning_product_type"),
        Index("idx_st_transaction_date", "company_id", "warehouse_id", "transaction_date"),
        Index("idx_st_reference", "reference_type", "reference_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )

    # Stock identity dimensions (nullable based on warehouse type)
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True
    )
    count_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("count_catalog.id"), nullable=True
    )
    # NULL = own company stock; non-null = tolling / external owner
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True
    )
    waste_type: Mapped[WasteType | None] = mapped_column(nullable=True)
    pkg_item_type: Mapped[PackagingItemType | None] = mapped_column(nullable=True)
    ginning_product_type: Mapped[GinningProductType | None] = mapped_column(nullable=True)

    # Transaction metadata
    transaction_type: Mapped[TransactionType] = mapped_column(nullable=False)
    direction: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # +1 or -1

    # Quantities
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    quantity_bags: Mapped[int | None] = mapped_column(nullable=True)
    quantity_kip: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    quantity_units: Mapped[int | None] = mapped_column(nullable=True)

    # Polymorphic source reference
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Denormalized snapshot (for query performance — frozen at insert)
    lot_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    count_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    posted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # NO updated_at — this table is immutable
