import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.modules.ginning_bale.models import GinningBale
from app.shared.base_repository import BaseRepository


class GinningBaleRepository(BaseRepository[GinningBale]):
    model = GinningBale

    async def exists_for_order(self, order_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(func.count(GinningBale.id)).where(GinningBale.production_order_id == order_id)
        )
        return (result.scalar_one() or 0) > 0

    async def total_net_kg_for_order(self, order_id: uuid.UUID) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(GinningBale.net_weight_kg), 0)).where(
                GinningBale.production_order_id == order_id
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        production_order_id: uuid.UUID | None = None,
    ) -> tuple[list[GinningBale], int]:
        conditions = [GinningBale.company_id == company_id]
        if production_order_id is not None:
            conditions.append(GinningBale.production_order_id == production_order_id)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(GinningBale)
            .where(*conditions)
            .order_by(GinningBale.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
