import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.contract.models import Contract
from app.modules.counterparty.models import Counterparty
from app.shared.base_repository import BaseRepository


class ContractRepository(BaseRepository[Contract]):
    model = Contract

    async def get_by_number(self, company_id: uuid.UUID, contract_number: str) -> Contract | None:
        result = await self.session.execute(
            select(Contract).where(
                Contract.company_id == company_id,
                Contract.contract_number == contract_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_counterparty(self, contract_id: uuid.UUID) -> Contract | None:
        result = await self.session.execute(
            select(Contract)
            .where(Contract.id == contract_id)
            .options(selectinload(Contract.counterparty))
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        counterparty_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Contract], int]:
        where = [Contract.company_id == company_id]
        if active_only:
            where.append(Contract.is_active.is_(True))
        if counterparty_id:
            where.append(Contract.counterparty_id == counterparty_id)
        if search:
            where.append(Contract.contract_number.ilike(f"%{search}%"))

        total = await self.count(*where)
        result = await self.session.execute(
            select(Contract)
            .where(*where)
            .options(selectinload(Contract.counterparty))
            .order_by(Contract.contract_date.desc(), Contract.contract_number)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
