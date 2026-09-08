from datetime import date
import uuid

from sqlalchemy import select

from app.modules.cotton_receiving.models import CottonPriceList, CottonReceiving
from app.shared.base_repository import BaseRepository
from app.shared.enums import CottonReceivingStatus


class CottonReceivingRepository(BaseRepository[CottonReceiving]):
    model = CottonReceiving

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        bunt_id: uuid.UUID | None = None,
        farmer_id: uuid.UUID | None = None,
        status: CottonReceivingStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[CottonReceiving], int]:
        conditions = [CottonReceiving.company_id == company_id]
        if bunt_id is not None:
            conditions.append(CottonReceiving.bunt_id == bunt_id)
        if farmer_id is not None:
            conditions.append(CottonReceiving.farmer_id == farmer_id)
        if status is not None:
            conditions.append(CottonReceiving.status == status)
        if date_from is not None:
            conditions.append(CottonReceiving.receiving_date >= date_from)
        if date_to is not None:
            conditions.append(CottonReceiving.receiving_date <= date_to)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(CottonReceiving)
            .where(*conditions)
            .order_by(CottonReceiving.receiving_date.desc(), CottonReceiving.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_posted_for_bunt(self, bunt_id: uuid.UUID) -> list[CottonReceiving]:
        result = await self.session.execute(
            select(CottonReceiving).where(
                CottonReceiving.bunt_id == bunt_id,
                CottonReceiving.status == CottonReceivingStatus.POSTED,
            )
        )
        return list(result.scalars().all())


class CottonPriceListRepository(BaseRepository[CottonPriceList]):
    model = CottonPriceList

    async def find_best_match(
        self,
        company_id: uuid.UUID,
        as_of: date,
        grade: str | None,
        variety: str | None,
        sort: str | None,
        quality_class: str | None,
    ) -> CottonPriceList | None:
        """
        Most-specific active rule wins: every non-NULL field on the rule must match
        the receiving's value; among matches, the rule with the most non-NULL fields
        (ties broken by latest effective_from) wins.
        """
        result = await self.session.execute(
            select(CottonPriceList).where(
                CottonPriceList.company_id == company_id,
                CottonPriceList.is_active.is_(True),
                CottonPriceList.effective_from <= as_of,
            )
        )
        candidates = [
            rule
            for rule in result.scalars().all()
            if (rule.grade is None or rule.grade == grade)
            and (rule.variety is None or rule.variety == variety)
            and (rule.sort is None or rule.sort == sort)
            and (rule.quality_class is None or rule.quality_class == quality_class)
        ]
        if not candidates:
            return None

        def specificity(rule: CottonPriceList) -> tuple[int, date]:
            score = sum(
                1
                for f in (rule.grade, rule.variety, rule.sort, rule.quality_class)
                if f is not None
            )
            return (score, rule.effective_from)

        return max(candidates, key=specificity)
