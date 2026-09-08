import uuid

from sqlalchemy import select

from app.modules.ginning_costing.models import GinningProductionCost
from app.shared.base_repository import BaseRepository


class GinningProductionCostRepository(BaseRepository[GinningProductionCost]):
    model = GinningProductionCost

    async def list_for_order(self, order_id: uuid.UUID) -> list[GinningProductionCost]:
        result = await self.session.execute(
            select(GinningProductionCost)
            .where(GinningProductionCost.production_order_id == order_id)
            .order_by(GinningProductionCost.created_at)
        )
        return list(result.scalars().all())
