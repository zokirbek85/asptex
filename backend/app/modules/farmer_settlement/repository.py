import uuid

from sqlalchemy import select

from app.modules.farmer_settlement.models import FarmerPayment
from app.shared.base_repository import BaseRepository
from app.shared.enums import FarmerPaymentStatus


class FarmerPaymentRepository(BaseRepository[FarmerPayment]):
    model = FarmerPayment

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        farmer_id: uuid.UUID | None = None,
        status: FarmerPaymentStatus | None = None,
    ) -> tuple[list[FarmerPayment], int]:
        conditions = [FarmerPayment.company_id == company_id]
        if farmer_id is not None:
            conditions.append(FarmerPayment.farmer_id == farmer_id)
        if status is not None:
            conditions.append(FarmerPayment.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(FarmerPayment)
            .where(*conditions)
            .order_by(FarmerPayment.payment_date.desc(), FarmerPayment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
