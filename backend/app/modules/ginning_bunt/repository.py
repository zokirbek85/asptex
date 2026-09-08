import uuid

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.modules.ginning_bunt.models import GinningBunt
from app.shared.base_repository import BaseRepository
from app.shared.enums import BuntStatus


class GinningBuntRepository(BaseRepository[GinningBunt]):
    model = GinningBunt

    async def get_scoped_with_lot(self, bunt_id: uuid.UUID, company_id: uuid.UUID) -> GinningBunt | None:
        result = await self.session.execute(
            select(GinningBunt)
            .options(joinedload(GinningBunt.lot))
            .where(GinningBunt.id == bunt_id, GinningBunt.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        warehouse_id: uuid.UUID | None = None,
        status: BuntStatus | None = None,
    ) -> tuple[list[GinningBunt], int]:
        conditions = [GinningBunt.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(GinningBunt.warehouse_id == warehouse_id)
        if status is not None:
            conditions.append(GinningBunt.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(GinningBunt)
            .options(joinedload(GinningBunt.lot))
            .where(*conditions)
            .order_by(GinningBunt.opened_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.unique().scalars().all()), total
