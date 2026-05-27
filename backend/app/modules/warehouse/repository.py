import uuid

from sqlalchemy import select

from app.modules.warehouse.models import Warehouse
from app.shared.base_repository import BaseRepository
from app.shared.enums import WarehouseType


class WarehouseRepository(BaseRepository[Warehouse]):
    model = Warehouse

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Warehouse | None:
        result = await self.session.execute(
            select(Warehouse).where(
                Warehouse.company_id == company_id,
                Warehouse.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        warehouse_type: WarehouseType | None = None,
    ) -> tuple[list[Warehouse], int]:
        where = [Warehouse.company_id == company_id]
        if active_only:
            where.append(Warehouse.is_active.is_(True))
        if warehouse_type:
            where.append(Warehouse.warehouse_type == warehouse_type)

        total = await self.count(*where)
        result = await self.session.execute(
            select(Warehouse)
            .where(*where)
            .order_by(Warehouse.sort_order, Warehouse.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
