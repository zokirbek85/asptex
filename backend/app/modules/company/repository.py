from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company.models import Company
from app.shared.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    async def get_by_tax_id(self, tax_id: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.tax_id == tax_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> tuple[list[Company], int]:
        where = []
        if active_only:
            where.append(Company.is_active.is_(True))
        if search:
            where.append(Company.name.ilike(f"%{search}%"))

        total = await self.count(*where)
        result = await self.session.execute(
            select(Company)
            .where(*where)
            .order_by(Company.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
