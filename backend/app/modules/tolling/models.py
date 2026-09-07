import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import TollingDistributionStatus, TollingLineType, TollingLotStatus


class TollingLot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tolling_lots"
    __table_args__ = (
        Index(
            "uq_one_open_tolling_lot",
            "company_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False, unique=True
    )
    status: Mapped[TollingLotStatus] = mapped_column(nullable=False, default=TollingLotStatus.OPEN)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    participants: Mapped[list["TollingLotParticipant"]] = relationship(
        "TollingLotParticipant",
        back_populates="tolling_lot",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    distributions: Mapped[list["TollingDistribution"]] = relationship(
        "TollingDistribution",
        back_populates="tolling_lot",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class TollingLotParticipant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tolling_lot_participants"
    __table_args__ = (
        UniqueConstraint("tolling_lot_id", "counterparty_id", name="uq_tolling_participant_lot_cp"),
    )

    tolling_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tolling_lots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    counterparty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    raw_kg_delivered: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    fee_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    fee_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    fee_rate_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tolling_lot: Mapped["TollingLot"] = relationship("TollingLot", back_populates="participants", lazy="noload")


class TollingDistribution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tolling_daily_distributions"
    __table_args__ = (
        UniqueConstraint("tolling_lot_id", "distribution_date", name="uq_tolling_dist_lot_date"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    tolling_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tolling_lots.id"), nullable=False, index=True
    )
    distribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_fg_kg_total: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    status: Mapped[TollingDistributionStatus] = mapped_column(
        nullable=False, default=TollingDistributionStatus.DRAFT
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    tolling_lot: Mapped["TollingLot"] = relationship("TollingLot", back_populates="distributions", lazy="noload")
    lines: Mapped[list["TollingDistributionLine"]] = relationship(
        "TollingDistributionLine",
        back_populates="distribution",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    raw_intakes: Mapped[list["TollingDailyRawIntake"]] = relationship(
        "TollingDailyRawIntake",
        back_populates="distribution",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class TollingDailyRawIntake(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tolling_daily_raw_intakes"

    distribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tolling_daily_distributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tolling_lot_participants.id"), nullable=False
    )
    raw_kg_received_today: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    distribution: Mapped["TollingDistribution"] = relationship(
        "TollingDistribution", back_populates="raw_intakes", lazy="noload"
    )
    participant: Mapped["TollingLotParticipant"] = relationship(
        "TollingLotParticipant", lazy="noload"
    )


class TollingDistributionLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tolling_distribution_lines"

    distribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tolling_daily_distributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tolling_lot_participants.id"), nullable=True
    )
    line_type: Mapped[TollingLineType] = mapped_column(nullable=False)
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True
    )
    gross_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    fee_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    net_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    ownership_share_pct: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    fee_pct_applied: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    fee_amount_uzs: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fee_amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stock_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    distribution: Mapped["TollingDistribution"] = relationship(
        "TollingDistribution", back_populates="lines", lazy="noload"
    )
    participant: Mapped["TollingLotParticipant | None"] = relationship(
        "TollingLotParticipant", lazy="noload"
    )
