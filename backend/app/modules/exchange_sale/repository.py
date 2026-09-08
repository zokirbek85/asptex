from datetime import date
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.exchange_sale.models import ExchangeSale, ExchangeSaleCancellation
from app.shared.base_repository import BaseRepository
from app.shared.enums import ExchangeSaleStatus


class ExchangeSaleRepository(BaseRepository[ExchangeSale]):
    model = ExchangeSale

    async def get_with_lines(self, sale_id: uuid.UUID, company_id: uuid.UUID) -> ExchangeSale | None:
        result = await self.session.execute(
            select(ExchangeSale)
            .options(selectinload(ExchangeSale.lines), selectinload(ExchangeSale.cancellations))
            .where(ExchangeSale.id == sale_id, ExchangeSale.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        warehouse_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: ExchangeSaleStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[ExchangeSale], int]:
        conditions = [ExchangeSale.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(ExchangeSale.warehouse_id == warehouse_id)
        if customer_id is not None:
            conditions.append(ExchangeSale.customer_id == customer_id)
        if status is not None:
            conditions.append(ExchangeSale.status == status)
        if date_from is not None:
            conditions.append(ExchangeSale.sale_date >= date_from)
        if date_to is not None:
            conditions.append(ExchangeSale.sale_date <= date_to)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(ExchangeSale)
            .options(selectinload(ExchangeSale.lines))
            .where(*conditions)
            .order_by(ExchangeSale.sale_date.desc(), ExchangeSale.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def save_cancellation(self, cancellation: ExchangeSaleCancellation) -> ExchangeSaleCancellation:
        self.session.add(cancellation)
        await self.session.flush()
        return cancellation
