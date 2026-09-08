import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.ginning_production.models import GinningProductionOrder
from app.shared.base_repository import BaseRepository
from app.shared.enums import GinningProductionStatus


class GinningProductionOrderRepository(BaseRepository[GinningProductionOrder]):
    model = GinningProductionOrder

    async def get_scoped_with_lines(
        self, order_id: uuid.UUID, company_id: uuid.UUID
    ) -> GinningProductionOrder | None:
        result = await self.session.execute(
            select(GinningProductionOrder)
            .options(
                selectinload(GinningProductionOrder.inputs),
                selectinload(GinningProductionOrder.outputs),
            )
            .where(GinningProductionOrder.id == order_id, GinningProductionOrder.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        status: GinningProductionStatus | None = None,
    ) -> tuple[list[GinningProductionOrder], int]:
        conditions = [GinningProductionOrder.company_id == company_id]
        if status is not None:
            conditions.append(GinningProductionOrder.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(GinningProductionOrder)
            .options(
                selectinload(GinningProductionOrder.inputs),
                selectinload(GinningProductionOrder.outputs),
            )
            .where(*conditions)
            .order_by(GinningProductionOrder.production_date.desc(), GinningProductionOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
