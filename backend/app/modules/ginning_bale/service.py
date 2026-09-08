from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.ginning_bale.models import GinningBale
from app.modules.ginning_bale.repository import GinningBaleRepository
from app.modules.ginning_bale.schemas import (
    GinningBaleCreate,
    GinningBaleCreateResult,
    GinningBaleResponse,
)
from app.modules.ginning_production.repository import GinningProductionOrderRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, GinningProductionStatus, GinningProductType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_ginning_bale_number


class GinningBaleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GinningBaleRepository(session)
        self.order_repo = GinningProductionOrderRepository(session)
        self.audit = AuditService(session)

    def build_response(self, bale: GinningBale, production_number: str) -> GinningBaleResponse:
        return GinningBaleResponse(
            id=bale.id,
            company_id=bale.company_id,
            production_order_id=bale.production_order_id,
            production_number=production_number,
            warehouse_id=bale.warehouse_id,
            bale_number=bale.bale_number,
            production_date=bale.production_date,
            gross_weight_kg=bale.gross_weight_kg,
            tare_weight_kg=bale.tare_weight_kg,
            net_weight_kg=bale.net_weight_kg,
            moisture_pct=bale.moisture_pct,
            micronaire=bale.micronaire,
            staple_length_mm=bale.staple_length_mm,
            strength=bale.strength,
            color=bale.color,
            trash_pct=bale.trash_pct,
            grade=bale.grade,
            quality_class=bale.quality_class,
            status=bale.status,
            notes=bale.notes,
            created_at=bale.created_at,
        )

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        production_order_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[GinningBaleResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, production_order_id)
        order_number_cache: dict[uuid.UUID, str] = {}
        responses = []
        for b in items:
            if b.production_order_id not in order_number_cache:
                order = await self.order_repo.get_by_id(b.production_order_id)
                order_number_cache[b.production_order_id] = order.production_number if order else ""
            responses.append(self.build_response(b, order_number_cache[b.production_order_id]))
        return PaginatedResponse.build(responses, total, page, page_size)

    async def get(self, bale_id: uuid.UUID, company_id: uuid.UUID) -> GinningBale:
        return await self.repo.get_scoped_or_raise(bale_id, company_id, "GinningBale")

    async def create(
        self, company_id: uuid.UUID, data: GinningBaleCreate, ctx: AuditContext
    ) -> GinningBaleCreateResult:
        order = await self.order_repo.get_scoped_with_lines(data.production_order_id, company_id)
        if order is None:
            raise NotFoundError("GinningProductionOrder", data.production_order_id)
        if order.status != GinningProductionStatus.COMPLETED:
            raise BusinessRuleViolationError("Bales can only be created from a COMPLETED production order")

        net_weight_kg = data.gross_weight_kg - data.tare_weight_kg
        bale_number = await generate_ginning_bale_number(self.session, company_id)

        bale = await self.repo.create(
            company_id=company_id,
            production_order_id=data.production_order_id,
            warehouse_id=data.warehouse_id,
            bale_number=bale_number,
            production_date=order.production_date,
            gross_weight_kg=data.gross_weight_kg,
            tare_weight_kg=data.tare_weight_kg,
            net_weight_kg=net_weight_kg,
            moisture_pct=data.moisture_pct,
            micronaire=data.micronaire,
            staple_length_mm=data.staple_length_mm,
            strength=data.strength,
            color=data.color,
            trash_pct=data.trash_pct,
            grade=data.grade,
            quality_class=data.quality_class,
            notes=data.notes,
            created_by=ctx.actor_id,
        )

        fiber_output_total = sum(
            (o.quantity_kg for o in order.outputs if o.product_type == GinningProductType.FIBER),
            Decimal("0"),
        )
        bales_total = await self.repo.total_net_kg_for_order(order.id)
        warning = None
        if fiber_output_total > 0 and bales_total > fiber_output_total:
            warning = (
                f"Bale weights ({bales_total} kg) now exceed the order's posted fiber output "
                f"({fiber_output_total} kg) — please verify."
            )

        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_bale",
            action=AuditAction.CREATE,
            entity_id=bale.id,
            entity_display=bale.bale_number,
            after_data={"net_weight_kg": str(net_weight_kg), "production_order": order.production_number},
        )

        return GinningBaleCreateResult(
            bale=self.build_response(bale, order.production_number),
            reconciliation_warning=warning,
        )
