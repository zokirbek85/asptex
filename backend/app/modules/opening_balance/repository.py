import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.opening_balance.models import OpeningBalanceEntry, OpeningBalanceLine
from app.shared.base_repository import BaseRepository
from app.shared.enums import AdjustmentStatus


class OpeningBalanceRepository(BaseRepository[OpeningBalanceEntry]):
    model = OpeningBalanceEntry

    async def get_with_lines(
        self, entry_id: uuid.UUID, company_id: uuid.UUID
    ) -> OpeningBalanceEntry | None:
        result = await self.session.execute(
            select(OpeningBalanceEntry)
            .options(selectinload(OpeningBalanceEntry.lines))
            .where(
                OpeningBalanceEntry.id == entry_id,
                OpeningBalanceEntry.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: AdjustmentStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[OpeningBalanceEntry], int]:
        conditions = [OpeningBalanceEntry.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(OpeningBalanceEntry.warehouse_id == warehouse_id)
        if status is not None:
            conditions.append(OpeningBalanceEntry.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(OpeningBalanceEntry)
            .options(selectinload(OpeningBalanceEntry.lines))
            .where(*conditions)
            .order_by(OpeningBalanceEntry.balance_date.desc(), OpeningBalanceEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def replace_lines(
        self,
        entry: OpeningBalanceEntry,
        lines_data: list[dict],
    ) -> OpeningBalanceEntry:
        for line in list(entry.lines):
            await self.session.delete(line)
        await self.session.flush()

        for idx, ld in enumerate(lines_data, start=1):
            line = OpeningBalanceLine(
                entry_id=entry.id,
                line_number=idx,
                **ld,
            )
            self.session.add(line)

        await self.session.flush()
        await self.session.refresh(entry)
        return entry
