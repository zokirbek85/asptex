import uuid

from sqlalchemy import select

from app.modules.count_catalog.models import CountCatalog
from app.shared.base_repository import BaseRepository


class CountCatalogRepository(BaseRepository[CountCatalog]):
    model = CountCatalog

    async def get_by_value(
        self, company_id: uuid.UUID, count_value: str
    ) -> CountCatalog | None:
        result = await self.session.execute(
            select(CountCatalog).where(
                CountCatalog.company_id == company_id,
                CountCatalog.count_value == count_value,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> tuple[list[CountCatalog], int]:
        where = [CountCatalog.company_id == company_id]
        if active_only:
            where.append(CountCatalog.is_active.is_(True))
        if search:
            from sqlalchemy import or_
            pattern = f"%{search}%"
            where.append(
                or_(
                    CountCatalog.count_value.ilike(pattern),
                    CountCatalog.yarn_type.ilike(pattern),
                )
            )

        total = await self.count(*where)
        result = await self.session.execute(
            select(CountCatalog)
            .where(*where)
            .order_by(CountCatalog.count_value)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
