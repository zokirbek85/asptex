from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.tolling.models import (
    TollingDailyRawIntake,
    TollingDistribution,
    TollingDistributionLine,
    TollingLot,
    TollingLotParticipant,
)
from app.shared.base_repository import BaseRepository
from app.shared.enums import TollingDistributionStatus, TollingLotStatus


class TollingLotRepository(BaseRepository[TollingLot]):
    model = TollingLot

    async def get_active(self, company_id: uuid.UUID) -> TollingLot | None:
        result = await self.session.execute(
            select(TollingLot)
            .options(
                selectinload(TollingLot.participants),
            )
            .where(
                TollingLot.company_id == company_id,
                TollingLot.status == TollingLotStatus.OPEN,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_participants(
        self, lot_id: uuid.UUID, company_id: uuid.UUID
    ) -> TollingLot | None:
        result = await self.session.execute(
            select(TollingLot)
            .options(selectinload(TollingLot.participants))
            .where(TollingLot.id == lot_id, TollingLot.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def has_open_lot(self, company_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(TollingLot.id).where(
                TollingLot.company_id == company_id,
                TollingLot.status == TollingLotStatus.OPEN,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None


class TollingParticipantRepository(BaseRepository[TollingLotParticipant]):
    model = TollingLotParticipant

    async def get_active_for_lot(self, tolling_lot_id: uuid.UUID) -> list[TollingLotParticipant]:
        result = await self.session.execute(
            select(TollingLotParticipant).where(
                TollingLotParticipant.tolling_lot_id == tolling_lot_id,
                TollingLotParticipant.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def has_distributions(self, participant_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(TollingDailyRawIntake.id)
            .where(TollingDailyRawIntake.participant_id == participant_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


class TollingDistributionRepository(BaseRepository[TollingDistribution]):
    model = TollingDistribution

    async def get_full(
        self, dist_id: uuid.UUID, company_id: uuid.UUID
    ) -> TollingDistribution | None:
        result = await self.session.execute(
            select(TollingDistribution)
            .options(
                selectinload(TollingDistribution.lines),
                selectinload(TollingDistribution.raw_intakes).selectinload(TollingDailyRawIntake.participant),
            )
            .where(TollingDistribution.id == dist_id, TollingDistribution.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_lot_date(
        self, tolling_lot_id: uuid.UUID, distribution_date: date
    ) -> TollingDistribution | None:
        result = await self.session.execute(
            select(TollingDistribution).where(
                TollingDistribution.tolling_lot_id == tolling_lot_id,
                TollingDistribution.distribution_date == distribution_date,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_lot(
        self,
        company_id: uuid.UUID,
        tolling_lot_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: TollingDistributionStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TollingDistribution], int]:
        conditions = [TollingDistribution.company_id == company_id]
        if tolling_lot_id:
            conditions.append(TollingDistribution.tolling_lot_id == tolling_lot_id)
        if date_from:
            conditions.append(TollingDistribution.distribution_date >= date_from)
        if date_to:
            conditions.append(TollingDistribution.distribution_date <= date_to)
        if status:
            conditions.append(TollingDistribution.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(TollingDistribution)
            .options(
                selectinload(TollingDistribution.lines),
                selectinload(TollingDistribution.raw_intakes).selectinload(TollingDailyRawIntake.participant),
            )
            .where(*conditions)
            .order_by(TollingDistribution.distribution_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def replace_lines(
        self,
        distribution: TollingDistribution,
        lines_data: list[dict],
    ) -> None:
        for line in list(distribution.lines):
            await self.session.delete(line)
        await self.session.flush()
        for ld in lines_data:
            self.session.add(TollingDistributionLine(distribution_id=distribution.id, **ld))
        await self.session.flush()

    async def replace_raw_intakes(
        self,
        distribution: TollingDistribution,
        intakes_data: list[dict],
    ) -> None:
        for ri in list(distribution.raw_intakes):
            await self.session.delete(ri)
        await self.session.flush()
        for rd in intakes_data:
            self.session.add(TollingDailyRawIntake(distribution_id=distribution.id, **rd))
        await self.session.flush()

    async def count_confirmed_for_lot(self, tolling_lot_id: uuid.UUID) -> int:
        return await self.count(
            TollingDistribution.tolling_lot_id == tolling_lot_id,
            TollingDistribution.status == TollingDistributionStatus.CONFIRMED,
        )

    async def sum_fg_for_participant(
        self,
        tolling_lot_id: uuid.UUID,
        counterparty_id: uuid.UUID,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Returns (total_gross_kg, total_fee_kg, total_net_kg) from CONFIRMED
        distribution lines for the given participant.
        """
        from decimal import Decimal as D
        from sqlalchemy import func as sqlfunc
        from app.shared.enums import TollingLineType

        result = await self.session.execute(
            select(
                sqlfunc.coalesce(sqlfunc.sum(TollingDistributionLine.gross_kg), 0).label("gross"),
                sqlfunc.coalesce(sqlfunc.sum(TollingDistributionLine.fee_kg), 0).label("fee"),
                sqlfunc.coalesce(sqlfunc.sum(TollingDistributionLine.net_kg), 0).label("net"),
            )
            .join(TollingDistribution, TollingDistributionLine.distribution_id == TollingDistribution.id)
            .where(
                TollingDistribution.tolling_lot_id == tolling_lot_id,
                TollingDistribution.status == TollingDistributionStatus.CONFIRMED,
                TollingDistributionLine.counterparty_id == counterparty_id,
                TollingDistributionLine.line_type == TollingLineType.OWNER_NET,
            )
        )
        row = result.one()
        return D(str(row.gross)), D(str(row.fee)), D(str(row.net))

    async def sum_fg_for_lot(self, tolling_lot_id: uuid.UUID) -> float:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.coalesce(func.sum(TollingDistribution.daily_fg_kg_total), 0)).where(
                TollingDistribution.tolling_lot_id == tolling_lot_id,
                TollingDistribution.status == TollingDistributionStatus.CONFIRMED,
            )
        )
        return float(result.scalar_one() or 0)
