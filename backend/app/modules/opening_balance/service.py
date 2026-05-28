from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.opening_balance.models import OpeningBalanceEntry
from app.modules.opening_balance.repository import OpeningBalanceRepository
from app.modules.opening_balance.schemas import (
    OpeningBalanceCreate,
    OpeningBalanceLineCreate,
    OpeningBalanceLineResponse,
    OpeningBalanceResponse,
)
from app.modules.audit.service import AuditService
from app.modules.stock.repository import StockRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AdjustmentStatus, AuditAction, TransactionType
from app.shared.schemas import PaginatedResponse


class OpeningBalanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpeningBalanceRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    def _line_resp(self, line) -> OpeningBalanceLineResponse:
        return OpeningBalanceLineResponse(
            id=line.id,
            line_number=line.line_number,
            lot_id=line.lot_id,
            count_id=line.count_id,
            owner_id=line.owner_id,
            waste_type=line.waste_type,
            pkg_item_type=line.pkg_item_type,
            quantity_kg=Decimal(str(line.quantity_kg)),
            quantity_bags=line.quantity_bags,
            quantity_kip=Decimal(str(line.quantity_kip)) if line.quantity_kip is not None else None,
            quantity_units=line.quantity_units,
            lot_number=line.lot_number,
            count_value=line.count_value,
            owner_name=line.owner_name,
            transaction_id=line.transaction_id,
            notes=line.notes,
            created_at=line.created_at,
        )

    def _build_response(self, entry: OpeningBalanceEntry) -> OpeningBalanceResponse:
        return OpeningBalanceResponse(
            id=entry.id,
            company_id=entry.company_id,
            warehouse_id=entry.warehouse_id,
            balance_date=entry.balance_date,
            status=entry.status,
            notes=entry.notes,
            lines=[self._line_resp(l) for l in (entry.lines or [])],
            posted_at=entry.posted_at,
            posted_by=entry.posted_by,
            created_by=entry.created_by,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    async def create(
        self,
        company_id: uuid.UUID,
        data: OpeningBalanceCreate,
        ctx: AuditContext,
    ) -> OpeningBalanceResponse:
        entry = await self.repo.create(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            balance_date=data.balance_date,
            status=AdjustmentStatus.DRAFT,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="opening_balance",
            action=AuditAction.CREATE,
            entity_id=entry.id,
            entity_display=str(data.balance_date),
            after_data={"warehouse_id": str(data.warehouse_id), "balance_date": str(data.balance_date)},
        )
        # Reload with lines to avoid lazy-load outside greenlet
        entry = await self.repo.get_with_lines(entry.id)
        return self._build_response(entry)

    async def get(self, entry_id: uuid.UUID) -> OpeningBalanceResponse:
        entry = await self.repo.get_with_lines(entry_id)
        if entry is None:
            raise NotFoundError("OpeningBalanceEntry", entry_id)
        return self._build_response(entry)

    async def list(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: AdjustmentStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[OpeningBalanceResponse]:
        items, total = await self.repo.list_paginated(company_id, warehouse_id, status, page, page_size)
        return PaginatedResponse.build(
            [self._build_response(e) for e in items], total, page, page_size
        )

    async def update_lines(
        self,
        entry_id: uuid.UUID,
        lines: list[OpeningBalanceLineCreate],
        ctx: AuditContext,
    ) -> OpeningBalanceResponse:
        entry = await self.repo.get_with_lines(entry_id)
        if entry is None:
            raise NotFoundError("OpeningBalanceEntry", entry_id)
        if entry.status != AdjustmentStatus.DRAFT:
            raise BusinessRuleViolationError("Faqat DRAFT holatidagi yozuvni tahrirlash mumkin")

        lines_dicts = [
            {
                "lot_id": line.lot_id,
                "count_id": line.count_id,
                "owner_id": line.owner_id,
                "waste_type": line.waste_type,
                "pkg_item_type": line.pkg_item_type,
                "quantity_kg": float(line.quantity_kg),
                "quantity_bags": line.quantity_bags,
                "quantity_kip": float(line.quantity_kip) if line.quantity_kip is not None else None,
                "quantity_units": line.quantity_units,
                "lot_number": None,
                "count_value": None,
                "owner_name": None,
                "transaction_id": None,
                "notes": line.notes,
            }
            for line in lines
        ]

        # Resolve denormalized snapshots from DB
        if any(d["lot_id"] or d["count_id"] or d["owner_id"] for d in lines_dicts):
            lot_ids = {d["lot_id"] for d in lines_dicts if d["lot_id"]}
            count_ids = {d["count_id"] for d in lines_dicts if d["count_id"]}
            owner_ids = {d["owner_id"] for d in lines_dicts if d["owner_id"]}

            from sqlalchemy import select
            from app.modules.lot.models import Lot
            from app.modules.count_catalog.models import CountCatalog
            from app.modules.counterparty.models import Counterparty

            lots: dict[uuid.UUID, str] = {}
            counts: dict[uuid.UUID, str] = {}
            owners: dict[uuid.UUID, str] = {}

            if lot_ids:
                rows = await self.session.execute(select(Lot.id, Lot.lot_number).where(Lot.id.in_(lot_ids)))
                lots = {r.id: r.lot_number for r in rows}
            if count_ids:
                rows = await self.session.execute(select(CountCatalog.id, CountCatalog.count_value).where(CountCatalog.id.in_(count_ids)))
                counts = {r.id: r.count_value for r in rows}
            if owner_ids:
                rows = await self.session.execute(select(Counterparty.id, Counterparty.name).where(Counterparty.id.in_(owner_ids)))
                owners = {r.id: r.name for r in rows}

            for d in lines_dicts:
                if d["lot_id"]:
                    d["lot_number"] = lots.get(d["lot_id"])
                if d["count_id"]:
                    d["count_value"] = counts.get(d["count_id"])
                if d["owner_id"]:
                    d["owner_name"] = owners.get(d["owner_id"])

        await self.repo.replace_lines(entry, lines_dicts)
        return self._build_response(entry)

    async def post(
        self,
        entry_id: uuid.UUID,
        ctx: AuditContext,
    ) -> OpeningBalanceResponse:
        entry = await self.repo.get_with_lines(entry_id)
        if entry is None:
            raise NotFoundError("OpeningBalanceEntry", entry_id)
        if entry.status != AdjustmentStatus.DRAFT:
            raise BusinessRuleViolationError("Boshlang'ich qoldiq allaqachon joylashtirilgan")
        if not entry.lines:
            raise BusinessRuleViolationError("Satr qo'shing")

        for line in entry.lines:
            tx = await self.stock_repo.post_transaction(
                company_id=entry.company_id,
                warehouse_id=entry.warehouse_id,
                transaction_type=TransactionType.OPENING_BALANCE,
                direction=1,
                quantity_kg=Decimal(str(line.quantity_kg)),
                transaction_date=entry.balance_date,
                posted_by=ctx.actor_id,
                reference_type="OPENING_BALANCE",
                reference_id=entry.id,
                reference_line_id=line.id,
                lot_id=line.lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                pkg_item_type=line.pkg_item_type,
                quantity_bags=line.quantity_bags,
                quantity_kip=Decimal(str(line.quantity_kip)) if line.quantity_kip is not None else None,
                quantity_units=line.quantity_units,
                lot_number=line.lot_number,
                count_value=line.count_value,
                owner_name=line.owner_name,
                notes=line.notes,
            )
            line.transaction_id = tx.id

        entry.status = AdjustmentStatus.POSTED
        entry.posted_at = datetime.now(timezone.utc)
        entry.posted_by = ctx.actor_id
        await self.repo.save(entry)

        await self.audit.log(
            ctx=ctx,
            entity_type="opening_balance",
            action=AuditAction.POST,
            entity_id=entry.id,
            entity_display=str(entry.balance_date),
            after_data={"status": "POSTED", "lines": len(entry.lines)},
        )
        return self._build_response(entry)

    async def delete(
        self,
        entry_id: uuid.UUID,
        ctx: AuditContext,
    ) -> None:
        entry = await self.repo.get_with_lines(entry_id)
        if entry is None:
            raise NotFoundError("OpeningBalanceEntry", entry_id)
        if entry.status != AdjustmentStatus.DRAFT:
            raise BusinessRuleViolationError("Faqat DRAFT holatidagi yozuvni o'chirish mumkin")
        await self.repo.delete(entry)
        await self.audit.log(
            ctx=ctx,
            entity_type="opening_balance",
            action=AuditAction.DELETE,
            entity_id=entry_id,
            entity_display=str(entry.balance_date),
        )
