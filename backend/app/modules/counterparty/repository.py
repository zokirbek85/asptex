import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.counterparty.models import Counterparty, CounterpartyContact
from app.shared.base_repository import BaseRepository
from app.shared.enums import CounterpartyType


class CounterpartyRepository(BaseRepository[Counterparty]):
    model = Counterparty

    async def get_with_contacts(self, counterparty_id: uuid.UUID) -> Counterparty | None:
        result = await self.session.execute(
            select(Counterparty)
            .where(Counterparty.id == counterparty_id)
            .options(selectinload(Counterparty.contacts))
        )
        return result.scalar_one_or_none()

    async def get_by_tax_id(
        self, company_id: uuid.UUID, tax_id: str
    ) -> Counterparty | None:
        result = await self.session.execute(
            select(Counterparty).where(
                Counterparty.company_id == company_id,
                Counterparty.tax_id == tax_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        counterparty_type: CounterpartyType | None = None,
        search: str | None = None,
    ) -> tuple[list[Counterparty], int]:
        where = [Counterparty.company_id == company_id]
        if active_only:
            where.append(Counterparty.is_active.is_(True))
        if counterparty_type:
            where.append(Counterparty.counterparty_type == counterparty_type)
        if search:
            from sqlalchemy import or_
            pattern = f"%{search}%"
            where.append(
                or_(
                    Counterparty.name.ilike(pattern),
                    Counterparty.short_name.ilike(pattern),
                    Counterparty.tax_id.ilike(pattern),
                )
            )

        total = await self.count(*where)
        result = await self.session.execute(
            select(Counterparty)
            .where(*where)
            .options(selectinload(Counterparty.contacts))
            .order_by(Counterparty.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


class CounterpartyContactRepository(BaseRepository[CounterpartyContact]):
    model = CounterpartyContact
