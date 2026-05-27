import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import LotStatus


class Lot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lots"
    __table_args__ = (
        UniqueConstraint("company_id", "lot_number", name="uq_lot_company_number"),
        UniqueConstraint("company_id", "year", "sequence_number", name="uq_lot_company_year_seq"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    lot_number: Mapped[str] = mapped_column(String(20), nullable=False)          # "2026-005"
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[LotStatus] = mapped_column(nullable=False, default=LotStatus.OPEN)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class LotNumberSequence(Base):
    """Sequence counter for lot number generation — used with SELECT FOR UPDATE."""
    __tablename__ = "lot_number_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
