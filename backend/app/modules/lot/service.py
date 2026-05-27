import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.lot.models import Lot
from app.modules.lot.repository import LotRepository
from app.modules.lot.schemas import LotClose, LotCreate, LotReopen, LotUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, LotStatus
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_lot_number


class LotService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LotRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        status: LotStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[Lot]:
        items, total = await self.repo.list_paginated(
            company_id, page, page_size, status, search
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, lot_id: uuid.UUID) -> Lot:
        return await self.repo.get_by_id_or_raise(lot_id, "Lot")

    async def create(
        self, company_id: uuid.UUID, data: LotCreate, ctx: AuditContext
    ) -> Lot:
        lot_number, year, seq = await generate_lot_number(self.session, company_id)
        lot = await self.repo.create(
            company_id=company_id,
            lot_number=lot_number,
            year=year,
            sequence_number=seq,
            status=LotStatus.OPEN,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="lot",
            action=AuditAction.CREATE,
            entity_id=lot.id,
            entity_display=lot.lot_number,
            after_data={"lot_number": lot.lot_number, "year": year},
        )
        return lot

    async def update(self, lot_id: uuid.UUID, data: LotUpdate, ctx: AuditContext) -> Lot:
        lot = await self.repo.get_by_id_or_raise(lot_id, "Lot")
        if lot.status == LotStatus.BLOCKED:
            raise BusinessRuleViolationError("Cannot update a blocked lot")
        if data.notes is not None:
            lot.notes = data.notes
        await self.repo.save(lot)
        return lot

    async def close(
        self, lot_id: uuid.UUID, data: LotClose, ctx: AuditContext
    ) -> Lot:
        lot = await self.repo.get_by_id_or_raise(lot_id, "Lot")
        if lot.status != LotStatus.OPEN:
            raise BusinessRuleViolationError(
                f"Lot is already {lot.status.value}; only OPEN lots can be closed"
            )
        lot.status = LotStatus.CLOSED
        lot.closed_at = datetime.now(timezone.utc)
        lot.closed_by = ctx.actor_id
        lot.close_reason = data.reason
        lot.auto_closed = False
        await self.repo.save(lot)
        await self.audit.log(
            ctx=ctx,
            entity_type="lot",
            action=AuditAction.CLOSE,
            entity_id=lot.id,
            entity_display=lot.lot_number,
            after_data={"reason": data.reason},
        )
        return lot

    async def reopen(
        self, lot_id: uuid.UUID, data: LotReopen, ctx: AuditContext
    ) -> Lot:
        lot = await self.repo.get_by_id_or_raise(lot_id, "Lot")
        if lot.status == LotStatus.OPEN:
            raise BusinessRuleViolationError("Lot is already open")
        if lot.status == LotStatus.BLOCKED:
            raise BusinessRuleViolationError("Blocked lots must be unblocked before reopening")
        lot.status = LotStatus.OPEN
        lot.closed_at = None
        lot.closed_by = None
        lot.close_reason = None
        lot.auto_closed = False
        await self.repo.save(lot)
        await self.audit.log(
            ctx=ctx,
            entity_type="lot",
            action=AuditAction.REOPEN,
            entity_id=lot.id,
            entity_display=lot.lot_number,
            after_data={"reason": data.reason},
        )
        return lot

    async def block(self, lot_id: uuid.UUID, ctx: AuditContext) -> Lot:
        lot = await self.repo.get_by_id_or_raise(lot_id, "Lot")
        if lot.status == LotStatus.BLOCKED:
            raise BusinessRuleViolationError("Lot is already blocked")
        lot.status = LotStatus.BLOCKED
        await self.repo.save(lot)
        await self.audit.log(
            ctx=ctx,
            entity_type="lot",
            action=AuditAction.BLOCK,
            entity_id=lot.id,
            entity_display=lot.lot_number,
        )
        return lot

    async def unblock(self, lot_id: uuid.UUID, ctx: AuditContext) -> Lot:
        lot = await self.repo.get_by_id_or_raise(lot_id, "Lot")
        if lot.status != LotStatus.BLOCKED:
            raise BusinessRuleViolationError("Lot is not blocked")
        lot.status = LotStatus.CLOSED
        await self.repo.save(lot)
        await self.audit.log(
            ctx=ctx,
            entity_type="lot",
            action=AuditAction.REOPEN,
            entity_id=lot.id,
            entity_display=lot.lot_number,
            after_data={"action": "unblocked → CLOSED"},
        )
        return lot

    async def get_stock_summary(self, lot_id: uuid.UUID) -> "list[dict]":
        await self.repo.get_by_id_or_raise(lot_id, "Lot")
        return await self.repo.get_stock_summary(lot_id)
