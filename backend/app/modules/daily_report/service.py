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
    LotBalanceSummary,
    OpeningBalanceLine,
    OwnerBalanceLine,
    TollingBalanceSummary,
    TollingParticipantBalance,
    TollingWarning,
    WarehouseRunningBalance,
)
from app.modules.stock.repository import StockRepository
from app.modules.stock.service import StockService
from app.shared.base_service import AuditContext
from app.shared.enums import (
    AuditAction,
    LineCategory,
    ReportStatus,
    TollingDistributionStatus,
    TollingLotStatus,
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
    tx_type, direction = mapping
    # RECEIPT + owner_id set → tolling raw material receipt
    if (
        line.line_category == LineCategory.RECEIPT
        and line.owner_id is not None
        and line.waste_type is None
        and line.pkg_item_type is None
    ):
        tx_type = TransactionType.TOLLING_RAW_RECEIPT
    return tx_type, direction


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
            return await self.repo.get_with_lines(existing.id, company_id)

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
        return await self.repo.get_with_lines(report.id, company_id)

    async def get(self, report_id: uuid.UUID, company_id: uuid.UUID) -> DailyReport:
        report = await self.repo.get_with_lines(report_id, company_id)
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
        company_id: uuid.UUID,
        data: DailyReportSubmit,
        ctx: AuditContext,
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id, company_id)
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

    async def _check_tolling_mismatch(
        self,
        company_id: uuid.UUID,
        report_date: date,
    ) -> list[TollingWarning] | None:
        from app.modules.tolling.models import TollingLot, TollingDistribution
        from sqlalchemy import select as sa_select

        result = await self.session.execute(
            sa_select(TollingLot).where(
                TollingLot.company_id == company_id,
                TollingLot.status == TollingLotStatus.OPEN,
            )
        )
        active_lots = result.scalars().all()
        if not active_lots:
            return None

        warnings: list[TollingWarning] = []
        for tl in active_lots:
            dist_result = await self.session.execute(
                sa_select(TollingDistribution).where(
                    TollingDistribution.tolling_lot_id == tl.id,
                    TollingDistribution.distribution_date == report_date,
                )
            )
            dist = dist_result.scalar_one_or_none()
            if dist is None:
                warnings.append(TollingWarning(
                    tolling_lot_id=str(tl.id),
                    dist_exists=False,
                    dist_confirmed=False,
                    warning=f"Tolling lot mavjud, lekin {report_date} uchun taqsimot kiritilmagan",
                ))
            elif dist.status == TollingDistributionStatus.DRAFT:
                warnings.append(TollingWarning(
                    tolling_lot_id=str(tl.id),
                    dist_exists=True,
                    dist_confirmed=False,
                    distribution_id=str(dist.id),
                    warning=f"Tolling taqsimot DRAFT holatida — tasdiqlanmagan",
                ))
        return warnings if warnings else None

    async def submit(
        self,
        report_id: uuid.UUID,
        company_id: uuid.UUID,
        data: DailyReportSubmit,
        ctx: AuditContext,
    ) -> tuple[DailyReport, list[TollingWarning] | None]:
        report = await self.repo.get_with_lines(report_id, company_id)
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

        # Tolling mismatch warning (non-blocking) — only for FINISHED_GOODS warehouse
        tolling_warnings: list[TollingWarning] | None = None
        if wh is not None and wh.warehouse_type == WarehouseType.FINISHED_GOODS:
            production_inbound_total = sum(
                Decimal(str(line.quantity_kg))
                for line in report.lines
                if line.line_category == LineCategory.PRODUCTION_INBOUND
                and line.waste_type is None
            )
            if production_inbound_total > Decimal("0"):
                tolling_warnings = await self._check_tolling_mismatch(
                    company_id=report.company_id,
                    report_date=report.report_date,
                )

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
        return report, tolling_warnings

    async def get_warehouse_running_balance(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> WarehouseRunningBalance:
        from collections import defaultdict
        from app.modules.tolling.models import TollingLot, TollingLotParticipant
        from app.modules.tolling.repository import TollingDistributionRepository
        from app.modules.warehouse.models import Warehouse as WarehouseModel
        from app.modules.lot.models import Lot as LotModel
        from app.modules.counterparty.models import Counterparty
        from sqlalchemy import select as sa_select

        target_date = as_of_date or date.today()

        # 1. All stock balances for this warehouse
        raw_balances = await self.stock_repo.get_balances_for_warehouse(
            company_id=company_id,
            warehouse_id=warehouse_id,
            as_of_date=target_date,
        )

        # 2. Group by (lot_id, count_id)
        lot_count_groups: dict[tuple, list[dict]] = defaultdict(list)
        for row in raw_balances:
            key = (row["lot_id"], row["lot_number"], row["count_id"], row["count_value"])
            lot_count_groups[key].append(row)

        lot_summaries: list[LotBalanceSummary] = []
        for (lot_id, lot_number, count_id, count_value), rows in lot_count_groups.items():
            own_kg = 0.0
            tolling_kg = 0.0
            owner_lines: list[OwnerBalanceLine] = []
            for row in rows:
                qty = float(row["quantity_kg"])
                is_tolling = row["owner_id"] is not None
                owner_lines.append(OwnerBalanceLine(
                    owner_id=row["owner_id"],
                    owner_name=row["owner_name"],
                    quantity_kg=qty,
                    quantity_bags=row.get("total_bags"),
                    is_tolling=is_tolling,
                ))
                if is_tolling:
                    tolling_kg += qty
                else:
                    own_kg += qty
            lot_summaries.append(LotBalanceSummary(
                lot_id=lot_id,
                lot_number=lot_number,
                count_id=count_id,
                count_value=count_value,
                total_kg=own_kg + tolling_kg,
                own_kg=own_kg,
                tolling_kg=tolling_kg,
                by_owner=owner_lines,
            ))

        # 3. Precompute per-owner balance from raw_balances for fast lookup
        # key: (lot_id, owner_id) → stock_kg
        balance_by_lot_owner: dict[tuple, float] = defaultdict(float)
        for row in raw_balances:
            if row["owner_id"] is not None:
                balance_by_lot_owner[(row["lot_id"], row["owner_id"])] += float(row["quantity_kg"])

        # 4. TollingLot summaries
        tl_result = await self.session.execute(
            sa_select(TollingLot)
            .where(TollingLot.company_id == company_id)
            .order_by(TollingLot.opened_at.desc())
        )
        tolling_lots = tl_result.scalars().all()

        # Batch-load counterparty names
        all_cp_ids: set[uuid.UUID] = set()
        for tl in tolling_lots:
            p_result = await self.session.execute(
                sa_select(TollingLotParticipant).where(
                    TollingLotParticipant.tolling_lot_id == tl.id,
                    TollingLotParticipant.is_active == True,
                )
            )
            for p in p_result.scalars().all():
                all_cp_ids.add(p.counterparty_id)

        cp_names: dict[uuid.UUID, str] = {}
        if all_cp_ids:
            cp_result = await self.session.execute(
                sa_select(Counterparty.id, Counterparty.name).where(Counterparty.id.in_(all_cp_ids))
            )
            cp_names = {r.id: r.name for r in cp_result}

        dist_repo = TollingDistributionRepository(self.session)
        tolling_summaries: list[TollingBalanceSummary] = []

        for tl in tolling_lots:
            lot = await self.session.get(LotModel, tl.lot_id)
            p_result = await self.session.execute(
                sa_select(TollingLotParticipant).where(
                    TollingLotParticipant.tolling_lot_id == tl.id,
                    TollingLotParticipant.is_active == True,
                )
            )
            participants = p_result.scalars().all()

            participant_balances: list[TollingParticipantBalance] = []
            for p in participants:
                raw_contract = float(p.raw_kg_delivered)
                raw_actual = float(await self.stock_repo.get_tolling_raw_actual(
                    company_id=company_id,
                    owner_id=p.counterparty_id,
                ))
                fg_gross, fg_fee, fg_net = await dist_repo.sum_fg_for_participant(
                    tolling_lot_id=tl.id,
                    counterparty_id=p.counterparty_id,
                )
                fg_stock = balance_by_lot_owner.get(
                    (tl.lot_id, p.counterparty_id), 0.0
                ) if lot else 0.0
                fg_shipped = float(await self.stock_repo.get_tolling_fg_shipped(
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    lot_id=tl.lot_id,
                    owner_id=p.counterparty_id,
                )) if lot else 0.0

                participant_balances.append(TollingParticipantBalance(
                    counterparty_id=p.counterparty_id,
                    counterparty_name=cp_names.get(p.counterparty_id, ""),
                    raw_kg_contract=raw_contract,
                    raw_kg_actual=raw_actual,
                    raw_kg_diff=raw_actual - raw_contract,
                    fg_gross_kg=float(fg_gross),
                    fg_fee_kg=float(fg_fee),
                    fg_net_kg=float(fg_net),
                    fg_stock_kg=fg_stock,
                    fg_shipped_kg=fg_shipped,
                ))

            tolling_summaries.append(TollingBalanceSummary(
                tolling_lot_id=tl.id,
                lot_number=lot.lot_number if lot else str(tl.id),
                status=tl.status.value,
                participants=participant_balances,
            ))

        total_own = sum(ls.own_kg for ls in lot_summaries)
        total_tolling = sum(ls.tolling_kg for ls in lot_summaries)

        wh = await self.session.get(WarehouseModel, warehouse_id)

        return WarehouseRunningBalance(
            warehouse_id=warehouse_id,
            warehouse_name=wh.name if wh else str(warehouse_id),
            as_of_date=target_date,
            lots=lot_summaries,
            total_kg=total_own + total_tolling,
            total_own_kg=total_own,
            total_tolling_kg=total_tolling,
            tolling_lots=tolling_summaries,
        )

    async def delete_draft(
        self, report_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext
    ) -> None:
        report = await self.repo.get_with_lines(report_id, company_id)
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

    async def close(
        self, report_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id, company_id)
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
        company_id: uuid.UUID,
        data: DailyReportReopen,
        ctx: AuditContext,
    ) -> DailyReport:
        report = await self.repo.get_with_lines(report_id, company_id)
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
