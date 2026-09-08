import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, UUIDPrimaryKeyMixin
from app.shared.enums import FarmerLedgerEntryType


class FarmerLedgerEntry(Base, UUIDPrimaryKeyMixin):
    """
    Append-only farmer payable/receivable ledger. NEVER update or delete rows.
    Balance = SUM(amount * direction), grouped by farmer_id.
    Mirrors StockTransaction's immutable-ledger design, applied to money instead of kg.
    Positive balance = amount the company still owes the farmer.
    """
    __tablename__ = "farmer_ledger_entries"
    __table_args__ = (
        CheckConstraint("direction IN (1, -1)", name="chk_fle_direction"),
        CheckConstraint("amount > 0", name="chk_fle_amount_positive"),
        Index("idx_fle_balance_key", "company_id", "farmer_id"),
        Index("idx_fle_reference", "reference_type", "reference_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False
    )

    entry_type: Mapped[FarmerLedgerEntryType] = mapped_column(nullable=False)
    direction: Mapped[int] = mapped_column(nullable=False)  # +1 or -1
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")

    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    posted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    farmer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # denormalized snapshot

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # NO updated_at — this table is immutable
