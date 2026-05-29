from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationError,
    NotFoundError,
    PreviousDayNotClosedError,
    ReportNotEditableError,
)
from app.modules.audit.service import AuditService
from app.modules.daily_report.models import DailyReport, DailyReportLine
from app.modules.daily_report.repository import DailyReportRepository
from app.modules.daily_report.schemas import (
    DailyReportCreate,
    DailyReportLineCreate,
    DailyReportReopen,
    DailyReportSubmit,
    OpeningBalanceLine,
)
from app.modules.stock.repository import StockRepository
from app.modules.stock.service import StockService
from app.shared.base_service import AuditContext
from app.shared.enums import (
    AuditAction,
    LineCategory,
    ReportStatus,
    TransactionType,
    WarehouseType,
)
from app.shared.schemas import PaginatedResponse

# Maps (LineCategory, has_waste, has_pkg) → (TransactionType, direction)
_LINE_TX_MAP: dict[tuple[LineCategory, bool, bool], tuple[TransactionType, int]] = {
    (LineCategory.PRODUCTION_INBOUND, False, False): (TransactionType.PRODUCTION_INBOUND, 1),
    (LineCategory.PRODUCTION_INBOUND, True, False):  (TransactionType.WASTE_INBOUND, 1),
    (LineCategory.RECEIPT, False, False):             (TransactionType.RECEIPT, 1),
    (LineCategory.RECEIPT, False, True):              (TransactionType.PACKAGING_INBOUND, 1),
    (LineCategory.PRODUCTION_ISSUE, False, False):    (TransactionType.PRODUCTION_ISSUE, -1),
    (LineCategory.SALE_OUTBOUND, False, False):       (TransactionType.SHIPMENT_OUTBOUND, -1),
    (LineCategory.SALE_OUTBOUND, True, False):        (TransactionType.WASTE_SALE_OUTBOUND, -1),
    (LineCategory.PACKAGING_ISSUE, False, True):      (TransactionType.PACKAGING_ISSUE_OUTBOUND, -1),
}


def _resolve_tx(line: DailyReportLineCreate) -> tuple[TransactionType, int]:
    key = (line.line_category, line.waste_type is not None, line.pkg_item_type is not None)
    mapping = _LINE_TX_MAP.get(key)
    if mapping is None:
        raise BusinessRuleViolationError(
            f"Invalid line_category / identity combination: {line.line_category}"
        )
    return mapping


class DailyReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DailyReportRepository(session)
        self.stock_repo = StockRepository(session)
        self.stock_svc = StockService(session)
        self.audit = AuditService(session)

    async def get_or_create(
        self,
        company_id: uuid.UUID,
        data: DailyReportCreate,
        ctx: AuditContext,
    ) -> DailyReport:
        existing = await self.repo.get_by_warehouse_date(
            company_id, data.warehouse_id, data.report_date
        )
        if existing:
            # Reload with lines eagerly so callers can access report.lines safely
            return await self.repo.get_with_lines(existing.id)

        report = await self.repo.create(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            report_date=data.report_date,
            status=ReportStatus.DRAFT,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="daily_report",
            action=AuditAction.CREATE,
            entity_id=report.id,
            entity_display=str(data.report_date),
            after_data={"warehouse_id": str(data.warehouse_id), "report_date": str(data.report_date)},
        )
        # Fresh report has empty lines; reload with selectinload for consistency
        return await self.repo.get_with_lines(report.id)

    async def get(self, report_id: uuid.UUID) -> DailyReport:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        return report

    async def list(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None,
        page: int,
        page_size: int,
        status: ReportStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PaginatedResponse[DailyReport]:
        items, total = await self.repo.list_paginated(
            company_id, warehouse_id, page, page_size, status, date_from, date_to
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get_opening_balance(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        report_date: date,
    ) -> list[OpeningBalanceLine]:
        as_of = report_date - timedelta(days=1)
        rows = await self.stock_repo.get_balances_for_warehouse(
            company_id=company_id,
            warehouse_id=warehouse_id,
            as_of_date=as_of,
        )
        return [OpeningBalanceLine(**row) for row in rows]

    async def update_lines(
        self,
        report_id: uuid.UUID,
        data: DailyReportSubmit,
        ctx: AuditContext,
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        if report.status != ReportStatus.DRAFT:
            raise ReportNotEditableError(report.status.value)

        lines_dicts = [
            {
                "line_category": line.line_category,
                "lot_id": line.lot_id,
                "count_id": line.count_id,
                "owner_id": line.owner_id,
                "waste_type": line.waste_type,
                "buyer_id": line.buyer_id,
                "pkg_item_type": line.pkg_item_type,
                "quantity_kg": float(line.quantity_kg),
                "quantity_bags": line.quantity_bags,
                "quantity_kip": float(line.quantity_kip) if line.quantity_kip is not None else None,
                "quantity_units": line.quantity_units,
                "notes": line.notes,
                "transaction_id": None,
            }
            for line in data.lines
        ]
        await self.repo.replace_lines(report, lines_dicts)
        return report

    async def submit(
        self,
        report_id: uuid.UUID,
        data: DailyReportSubmit,
        ctx: AuditContext,
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        if report.status != ReportStatus.DRAFT:
            raise ReportNotEditableError(report.status.value)

        # Check previous day is closed
        prev = await self.repo.get_previous_day_report(
            report.company_id, report.warehouse_id, report.report_date
        )
        if prev is not None and prev.status != ReportStatus.CLOSED:
            raise PreviousDayNotClosedError(str(report.report_date - timedelta(days=1)))

        # Load warehouse type to apply raw-cotton stock rules
        from app.modules.warehouse.models import Warehouse as WarehouseModel
        from app.modules.lot.models import Lot as LotModel
        wh = await self.session.get(WarehouseModel, report.warehouse_id)
        is_raw_cotton = wh is not None and wh.warehouse_type == WarehouseType.RAW_COTTON

        # Batch-load lot numbers for denormalization in stock transactions
        lot_ids = {line.lot_id for line in data.lines if line.lot_id}
        lot_number_map: dict[uuid.UUID, str] = {}
        if lot_ids:
            from sqlalchemy import select as sa_select
            rows = await self.session.execute(
                sa_select(LotModel.id, LotModel.lot_number).where(LotModel.id.in_(lot_ids))
            )
            lot_number_map = {r.id: r.lot_number for r in rows}

        # Replace lines with submitted set
        lines_dicts = [
            {
                "line_category": line.line_category,
                "lot_id": line.lot_id,
                "count_id": line.count_id,
                "owner_id": line.owner_id,
                "waste_type": line.waste_type,
                "buyer_id": line.buyer_id,
                "pkg_item_type": line.pkg_item_type,
                "quantity_kg": float(line.quantity_kg),
                "quantity_bags": line.quantity_bags,
                "quantity_kip": float(line.quantity_kip) if line.quantity_kip is not None else None,
                "quantity_units": line.quantity_units,
                "notes": line.notes,
                "transaction_id": None,
            }
            for line in data.lines
        ]
        await self.repo.replace_lines(report, lines_dicts)

        # Post transactions for each line
        for line in report.lines:
            kg_zero = Decimal(str(line.quantity_kg)) == Decimal("0")
            units_zero = not line.quantity_units or line.quantity_units == 0
            if kg_zero and units_zero:
                continue

            tx_type, direction = _resolve_tx(DailyReportLineCreate(
                line_category=line.line_category,
                lot_id=line.lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                buyer_id=line.buyer_id,
                pkg_item_type=line.pkg_item_type,
                quantity_kg=Decimal(str(line.quantity_kg)),
                quantity_bags=line.quantity_bags,
                quantity_kip=Decimal(str(line.quantity_kip)) if line.quantity_kip is not None else None,
                quantity_units=line.quantity_units,
                notes=line.notes,
            ))
            delta_kg = Decimal(str(line.quantity_kg)) * direction
            # Raw cotton is received without a lot (lot_id=NULL). When issuing
            # to production, the line's lot_id is the target FG lot (informational)
            # but the stock deduction must match the receipt's lot_id=NULL bucket.
            stock_lot_id = (
                None
                if is_raw_cotton and line.line_category == LineCategory.PRODUCTION_ISSUE
                else line.lot_id
            )
            await self.stock_svc.check_balance_and_warn(
                company_id=report.company_id,
                warehouse_id=report.warehouse_id,
                delta_kg=delta_kg,
                lot_id=stock_lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                pkg_item_type=line.pkg_item_type,
            )

            tx = await self.stock_repo.post_transaction(
                company_id=report.company_id,
                warehouse_id=report.warehouse_id,
                transaction_type=tx_type,
                direction=direction,
                quantity_kg=Decimal(str(line.quantity_kg)),
                transaction_date=report.report_date,
                posted_by=ctx.actor_id,
                reference_type="DAILY_REPORT",
                reference_id=report.id,
                reference_line_id=line.id,
                lot_id=stock_lot_id,
                lot_number=lot_number_map.get(stock_lot_id) if stock_lot_id else None,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                pkg_item_type=line.pkg_item_type,
                quantity_bags=line.quantity_bags,
                quantity_kip=Decimal(str(line.quantity_kip)) if line.quantity_kip is not None else None,
                quantity_units=line.quantity_units,
                notes=line.notes,
            )
            line.transaction_id = tx.id

        report.status = ReportStatus.SUBMITTED
        report.submitted_at = datetime.now(timezone.utc)
        report.submitted_by = ctx.actor_id
        await self.repo.save(report)

        await self.audit.log(
            ctx=ctx,
            entity_type="daily_report",
            action=AuditAction.SUBMIT,
            entity_id=report.id,
            entity_display=str(report.report_date),
            after_data={"status": "SUBMITTED", "lines": len(report.lines)},
        )
        return report

    async def delete_draft(self, report_id: uuid.UUID, ctx: AuditContext) -> None:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        if report.status != ReportStatus.DRAFT:
            raise BusinessRuleViolationError("Faqat DRAFT holatidagi hisobotni o'chirish mumkin")
        await self.session.delete(report)
        await self.audit.log(
            ctx=ctx,
            entity_type="daily_report",
            action=AuditAction.DELETE,
            entity_id=report.id,
            entity_display=str(report.report_date),
        )

    async def close(self, report_id: uuid.UUID, ctx: AuditContext) -> DailyReport:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        if report.status != ReportStatus.SUBMITTED:
            raise BusinessRuleViolationError(
                f"Only SUBMITTED reports can be closed, current: {report.status.value}"
            )
        report.status = ReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        report.closed_by = ctx.actor_id
        await self.repo.save(report)
        await self.audit.log(
            ctx=ctx,
            entity_type="daily_report",
            action=AuditAction.CLOSE,
            entity_id=report.id,
            entity_display=str(report.report_date),
        )
        return report

    async def reopen(
        self,
        report_id: uuid.UUID,
        data: DailyReportReopen,
        ctx: AuditContext,
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id)
        if report is None:
            raise NotFoundError("DailyReport", report_id)
        if report.status not in (ReportStatus.SUBMITTED, ReportStatus.CLOSED):
            raise BusinessRuleViolationError(
                f"Cannot reopen report in status: {report.status.value}"
            )

        # Reverse all posted transactions from this report
        for line in report.lines:
            if line.transaction_id is None:
                continue
            tx = await self.session.get(
                __import__("app.modules.stock.models", fromlist=["StockTransaction"]).StockTransaction,
                line.transaction_id,
            )
            if tx is not None:
                await self.stock_repo.post_transaction(
                    company_id=report.company_id,
                    warehouse_id=report.warehouse_id,
                    transaction_type=tx.transaction_type,
                    direction=tx.direction * -1,
                    quantity_kg=Decimal(str(tx.quantity_kg)),
                    transaction_date=report.report_date,
                    posted_by=ctx.actor_id,
                    reference_type="DAILY_REPORT",
                    reference_id=report.id,
                    reference_line_id=line.id,
                    lot_id=tx.lot_id,
                    count_id=tx.count_id,
                    owner_id=tx.owner_id,
                    waste_type=tx.waste_type,
                    pkg_item_type=tx.pkg_item_type,
                    quantity_bags=tx.quantity_bags,
                    quantity_kip=Decimal(str(tx.quantity_kip)) if tx.quantity_kip is not None else None,
                    quantity_units=tx.quantity_units,
                    notes=f"REOPEN reversal of tx {tx.id}",
                )
            line.transaction_id = None

        report.status = ReportStatus.DRAFT
        report.reopen_count = (report.reopen_count or 0) + 1
        report.last_reopened_at = datetime.now(timezone.utc)
        report.last_reopened_by = ctx.actor_id
        report.reopen_reason = data.reopen_reason
        report.submitted_at = None
        report.submitted_by = None
        report.closed_at = None
        report.closed_by = None
        await self.repo.save(report)

        await self.audit.log(
            ctx=ctx,
            entity_type="daily_report",
            action=AuditAction.REOPEN,
            entity_id=report.id,
            entity_display=str(report.report_date),
            after_data={"reason": data.reopen_reason, "reopen_count": report.reopen_count},
        )
        return report
