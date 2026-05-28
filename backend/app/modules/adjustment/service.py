from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.adjustment.models import InventoryAdjustment
from app.modules.adjustment.repository import AdjustmentRepository
from app.modules.adjustment.schemas import (
    AdjustmentCreate,
    AdjustmentLineCreate,
    AdjustmentLineResponse,
    AdjustmentResponse,
)
from app.modules.audit.service import AuditService
from app.modules.stock.repository import StockRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AdjustmentStatus, AuditAction, TransactionType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_adjustment_number


class AdjustmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AdjustmentRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    def _build_line_response(self, line) -> AdjustmentLineResponse:
        return AdjustmentLineResponse(
            id=line.id,
            line_number=line.line_number,
            lot_id=line.lot_id,
            count_id=line.count_id,
            owner_id=line.owner_id,
            waste_type=line.waste_type,
            pkg_item_type=line.pkg_item_type,
            quantity_kg_before=Decimal(str(line.quantity_kg_before)),
            quantity_kg_after=Decimal(str(line.quantity_kg_after)),
            bags_before=line.bags_before,
            bags_after=line.bags_after,
            units_before=line.units_before,
            units_after=line.units_after,
            transaction_id=line.transaction_id,
            notes=line.notes,
            created_at=line.created_at,
        )

    def _build_response(self, adj: InventoryAdjustment) -> AdjustmentResponse:
        return AdjustmentResponse(
            id=adj.id,
            company_id=adj.company_id,
            warehouse_id=adj.warehouse_id,
            adjustment_number=adj.adjustment_number,
            adjustment_date=adj.adjustment_date,
            reason=adj.reason,
            status=adj.status,
            lines=[self._build_line_response(l) for l in (adj.lines or [])],
            posted_at=adj.posted_at,
            posted_by=adj.posted_by,
            created_at=adj.created_at,
            updated_at=adj.updated_at,
        )

    async def create(
        self,
        company_id: uuid.UUID,
        data: AdjustmentCreate,
        ctx: AuditContext,
    ) -> AdjustmentResponse:
        number = await generate_adjustment_number(self.session, company_id)
        adj = await self.repo.create(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            adjustment_number=number,
            adjustment_date=data.adjustment_date,
            reason=data.reason,
            status=AdjustmentStatus.DRAFT,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="adjustment",
            action=AuditAction.CREATE,
            entity_id=adj.id,
            entity_display=number,
            after_data={"adjustment_number": number, "warehouse_id": str(data.warehouse_id)},
        )
        return self._build_response(adj)

    async def get(self, adjustment_id: uuid.UUID) -> AdjustmentResponse:
        adj = await self.repo.get_with_lines(adjustment_id)
        if adj is None:
            raise NotFoundError("InventoryAdjustment", adjustment_id)
        return self._build_response(adj)

    async def list(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: AdjustmentStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[AdjustmentResponse]:
        items, total = await self.repo.list_paginated(company_id, warehouse_id, status, page, page_size)
        return PaginatedResponse.build(
            [self._build_response(a) for a in items], total, page, page_size
        )

    async def update_lines(
        self,
        adjustment_id: uuid.UUID,
        lines: list[AdjustmentLineCreate],
        ctx: AuditContext,
    ) -> AdjustmentResponse:
        adj = await self.repo.get_with_lines(adjustment_id)
        if adj is None:
            raise NotFoundError("InventoryAdjustment", adjustment_id)
        if adj.status != AdjustmentStatus.DRAFT:
            raise BusinessRuleViolationError("Can only edit DRAFT adjustments")

        lines_dicts = []
        for line in lines:
            before = await self.stock_repo.get_balance(
                company_id=adj.company_id,
                warehouse_id=adj.warehouse_id,
                lot_id=line.lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                pkg_item_type=line.pkg_item_type,
            )
            lines_dicts.append({
                "lot_id": line.lot_id,
                "count_id": line.count_id,
                "owner_id": line.owner_id,
                "waste_type": line.waste_type,
                "pkg_item_type": line.pkg_item_type,
                "quantity_kg_before": float(before),
                "quantity_kg_after": float(line.quantity_kg_after),
                "bags_before": 0,
                "bags_after": line.bags_after,
                "units_before": 0,
                "units_after": line.units_after,
                "transaction_id": None,
                "notes": line.notes,
            })

        await self.repo.replace_lines(adj, lines_dicts)
        return self._build_response(adj)

    async def post(
        self,
        adjustment_id: uuid.UUID,
        ctx: AuditContext,
    ) -> AdjustmentResponse:
        adj = await self.repo.get_with_lines(adjustment_id)
        if adj is None:
            raise NotFoundError("InventoryAdjustment", adjustment_id)
        if adj.status != AdjustmentStatus.DRAFT:
            raise BusinessRuleViolationError("Adjustment is already posted")

        for line in adj.lines:
            before = Decimal(str(line.quantity_kg_before))
            after = Decimal(str(line.quantity_kg_after))
            delta = after - before
            if delta == Decimal("0"):
                continue

            if delta > 0:
                tx_type = TransactionType.ADJUSTMENT_POSITIVE
                direction = 1
                qty = delta
            else:
                tx_type = TransactionType.ADJUSTMENT_NEGATIVE
                direction = -1
                qty = abs(delta)

            tx = await self.stock_repo.post_transaction(
                company_id=adj.company_id,
                warehouse_id=adj.warehouse_id,
                transaction_type=tx_type,
                direction=direction,
                quantity_kg=qty,
                transaction_date=adj.adjustment_date,
                posted_by=ctx.actor_id,
                reference_type="ADJUSTMENT",
                reference_id=adj.id,
                reference_line_id=line.id,
                lot_id=line.lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                pkg_item_type=line.pkg_item_type,
                notes=line.notes,
            )
            line.transaction_id = tx.id

        adj.status = AdjustmentStatus.POSTED
        adj.posted_at = datetime.now(timezone.utc)
        adj.posted_by = ctx.actor_id
        await self.repo.save(adj)

        await self.audit.log(
            ctx=ctx,
            entity_type="adjustment",
            action=AuditAction.POST,
            entity_id=adj.id,
            entity_display=adj.adjustment_number,
            after_data={"status": "POSTED", "lines": len(adj.lines)},
        )
        return self._build_response(adj)
