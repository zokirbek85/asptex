from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.ginning_bunt.models import GinningBunt
from app.modules.ginning_bunt.repository import GinningBuntRepository
from app.modules.ginning_bunt.schemas import (
    BuntFarmerComposition,
    GinningBuntClose,
    GinningBuntCreate,
    GinningBuntDetailResponse,
    GinningBuntResponse,
)
from app.modules.lot.repository import LotRepository
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.repository import WarehouseRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, BuntStatus, LotStatus, WarehouseType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_lot_number


class GinningBuntService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GinningBuntRepository(session)
        self.lot_repo = LotRepository(session)
        self.warehouse_repo = WarehouseRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    def build_response(self, bunt: GinningBunt) -> GinningBuntResponse:
        return GinningBuntResponse(
            id=bunt.id,
            company_id=bunt.company_id,
            lot_id=bunt.lot_id,
            lot_number=bunt.lot.lot_number,
            warehouse_id=bunt.warehouse_id,
            status=bunt.status,
            opened_at=bunt.opened_at,
            closed_at=bunt.closed_at,
            close_reason=bunt.close_reason,
            notes=bunt.notes,
            created_at=bunt.created_at,
        )

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        warehouse_id: uuid.UUID | None = None,
        status: BuntStatus | None = None,
    ) -> PaginatedResponse[GinningBuntResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, warehouse_id, status)
        return PaginatedResponse.build([self.build_response(b) for b in items], total, page, page_size)

    async def get(self, bunt_id: uuid.UUID, company_id: uuid.UUID) -> GinningBunt:
        bunt = await self.repo.get_scoped_with_lot(bunt_id, company_id)
        if bunt is None:
            raise NotFoundError("GinningBunt", bunt_id)
        return bunt

    async def get_detail(self, bunt_id: uuid.UUID, company_id: uuid.UUID) -> GinningBuntDetailResponse:
        bunt = await self.get(bunt_id, company_id)
        balance = await self.get_balance(bunt, company_id)
        composition = await self.get_composition(bunt_id, company_id)
        base = self.build_response(bunt)
        return GinningBuntDetailResponse(**base.model_dump(), balance_kg=balance, composition=composition)

    async def get_balance(self, bunt: GinningBunt, company_id: uuid.UUID) -> Decimal:
        return await self.stock_repo.get_balance(
            company_id=company_id,
            warehouse_id=bunt.warehouse_id,
            lot_id=bunt.lot_id,
            owner_id=None,
        )

    async def get_composition(
        self, bunt_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[BuntFarmerComposition]:
        # Local import avoids a module-load cycle with cotton_receiving (which imports GinningBunt).
        from app.modules.cotton_receiving.models import CottonReceiving
        from app.shared.enums import CottonReceivingStatus

        result = await self.session.execute(
            select(
                CottonReceiving.farmer_id,
                CottonReceiving.farmer_name,
                func.sum(CottonReceiving.net_weight_kg).label("total_net_kg"),
                func.count(CottonReceiving.id).label("receiving_count"),
            )
            .where(
                CottonReceiving.company_id == company_id,
                CottonReceiving.bunt_id == bunt_id,
                CottonReceiving.status == CottonReceivingStatus.POSTED,
            )
            .group_by(CottonReceiving.farmer_id, CottonReceiving.farmer_name)
            .order_by(func.sum(CottonReceiving.net_weight_kg).desc())
        )
        return [
            BuntFarmerComposition(
                farmer_id=row.farmer_id,
                farmer_name=row.farmer_name,
                total_net_kg=Decimal(str(row.total_net_kg)),
                receiving_count=row.receiving_count,
            )
            for row in result
        ]

    async def create(
        self, company_id: uuid.UUID, data: GinningBuntCreate, ctx: AuditContext
    ) -> GinningBunt:
        warehouse = await self.warehouse_repo.get_scoped_or_raise(data.warehouse_id, company_id, "Warehouse")
        if warehouse.warehouse_type != WarehouseType.RAW_COTTON:
            raise BusinessRuleViolationError("Bunt warehouse must be a RAW_COTTON warehouse")

        lot_number, year, seq = await generate_lot_number(self.session, company_id)
        lot = await self.lot_repo.create(
            company_id=company_id,
            lot_number=lot_number,
            year=year,
            sequence_number=seq,
            status=LotStatus.OPEN,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        bunt = await self.repo.create(
            company_id=company_id,
            lot_id=lot.id,
            warehouse_id=data.warehouse_id,
            status=BuntStatus.OPEN,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        bunt.lot = lot
        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_bunt",
            action=AuditAction.CREATE,
            entity_id=bunt.id,
            entity_display=lot.lot_number,
            after_data={"lot_number": lot.lot_number, "warehouse_id": str(data.warehouse_id)},
        )
        return bunt

    async def close(
        self, bunt_id: uuid.UUID, company_id: uuid.UUID, data: GinningBuntClose, ctx: AuditContext
    ) -> GinningBunt:
        bunt = await self.get(bunt_id, company_id)
        if bunt.status != BuntStatus.OPEN:
            raise BusinessRuleViolationError(f"Bunt is already {bunt.status.value}")
        bunt.status = BuntStatus.CLOSED
        bunt.closed_at = datetime.now(timezone.utc)
        bunt.closed_by = ctx.actor_id
        bunt.close_reason = data.reason
        await self.repo.save(bunt)
        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_bunt",
            action=AuditAction.CLOSE,
            entity_id=bunt.id,
            entity_display=bunt.lot.lot_number,
            after_data={"reason": data.reason},
        )
        return bunt

    async def reopen(self, bunt_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext) -> GinningBunt:
        bunt = await self.get(bunt_id, company_id)
        if bunt.status != BuntStatus.CLOSED:
            raise BusinessRuleViolationError("Only a CLOSED bunt can be reopened")
        bunt.status = BuntStatus.OPEN
        bunt.closed_at = None
        bunt.closed_by = None
        bunt.close_reason = None
        await self.repo.save(bunt)
        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_bunt",
            action=AuditAction.REOPEN,
            entity_id=bunt.id,
            entity_display=bunt.lot.lot_number,
        )
        return bunt
