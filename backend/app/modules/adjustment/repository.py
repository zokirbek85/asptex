import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.adjustment.models import InventoryAdjustment, InventoryAdjustmentLine
from app.shared.base_repository import BaseRepository
from app.shared.enums import AdjustmentStatus


class AdjustmentRepository(BaseRepository[InventoryAdjustment]):
    model = InventoryAdjustment

    async def get_with_lines(self, adjustment_id: uuid.UUID) -> InventoryAdjustment | None:
        result = await self.session.execute(
            select(InventoryAdjustment)
            .options(selectinload(InventoryAdjustment.lines))
            .where(InventoryAdjustment.id == adjustment_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: AdjustmentStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InventoryAdjustment], int]:
        conditions = [InventoryAdjustment.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(InventoryAdjustment.warehouse_id == warehouse_id)
        if status is not None:
            conditions.append(InventoryAdjustment.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(InventoryAdjustment)
            .where(*conditions)
            .order_by(InventoryAdjustment.adjustment_date.desc(), InventoryAdjustment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def replace_lines(
        self,
        adjustment: InventoryAdjustment,
        lines_data: list[dict],
    ) -> InventoryAdjustment:
        for line in list(adjustment.lines):
            await self.session.delete(line)
        await self.session.flush()

        for idx, ld in enumerate(lines_data, start=1):
            line = InventoryAdjustmentLine(
                adjustment_id=adjustment.id,
                line_number=idx,
                **ld,
            )
            self.session.add(line)

        await self.session.flush()
        await self.session.refresh(adjustment)
        return adjustment
