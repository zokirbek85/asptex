import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import LineCategory, PackagingItemType, ReportStatus, WasteType


class DailyReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "warehouse_id", "report_date",
            name="uq_daily_report_company_warehouse_date"
        ),
        Index("idx_dr_warehouse_date", "company_id", "warehouse_id", "report_date"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(nullable=False, default=ReportStatus.DRAFT)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    last_reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reopened_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reopen_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reopen_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Relationships
    lines: Mapped[list["DailyReportLine"]] = relationship(
        "DailyReportLine", back_populates="report", cascade="all, delete-orphan",
        order_by="DailyReportLine.line_number",
    )


class DailyReportLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_report_lines"
    __table_args__ = (
        UniqueConstraint("daily_report_id", "line_number", name="uq_drl_report_line"),
        CheckConstraint("quantity_kg >= 0", name="chk_drl_qty"),
        Index("idx_drl_report", "daily_report_id"),
    )

    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    line_category: Mapped[LineCategory] = mapped_column(nullable=False)

    # Stock identity dimensions (nullable by warehouse type)
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
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True
    )
    pkg_item_type: Mapped[PackagingItemType | None] = mapped_column(nullable=True)

    # Quantities
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    quantity_bags: Mapped[int | None] = mapped_column(nullable=True)
    quantity_kip: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    quantity_units: Mapped[int | None] = mapped_column(nullable=True)

    # Linked transaction (set after report SUBMIT)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    report: Mapped["DailyReport"] = relationship("DailyReport", back_populates="lines")
