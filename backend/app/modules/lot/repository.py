import uuid

from sqlalchemy import func, select

from app.modules.count_catalog.models import CountCatalog
from app.modules.lot.models import Lot
from app.modules.stock.models import StockTransaction
from app.modules.warehouse.models import Warehouse
from app.shared.base_repository import BaseRepository
from app.shared.enums import LotStatus


class LotRepository(BaseRepository[Lot]):
    model = Lot

    async def get_by_number(self, company_id: uuid.UUID, lot_number: str) -> Lot | None:
        result = await self.session.execute(
            select(Lot).where(
                Lot.company_id == company_id,
                Lot.lot_number == lot_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        status: LotStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Lot], int]:
        where = [Lot.company_id == company_id]
        if status:
            where.append(Lot.status == status)
        if search:
            where.append(Lot.lot_number.ilike(f"%{search}%"))

        total = await self.count(*where)
        result = await self.session.execute(
            select(Lot)
            .where(*where)
            .order_by(Lot.year.desc(), Lot.sequence_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_stock_summary(self, lot_id: uuid.UUID) -> list[dict]:
        """
        Returns current stock breakdown by (warehouse, count, owner) for a lot.
        Only rows with non-zero balance are returned.
        """
        balance_expr = func.sum(
            StockTransaction.quantity_kg * StockTransaction.direction
        ).label("total_kg")

        result = await self.session.execute(
            select(
                StockTransaction.warehouse_id,
                Warehouse.name.label("warehouse_name"),
                StockTransaction.count_id,
                CountCatalog.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                balance_expr,
            )
            .join(Warehouse, Warehouse.id == StockTransaction.warehouse_id)
            .join(CountCatalog, CountCatalog.id == StockTransaction.count_id, isouter=True)
            .where(StockTransaction.lot_id == lot_id)
            .group_by(
                StockTransaction.warehouse_id,
                Warehouse.name,
                StockTransaction.count_id,
                CountCatalog.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
            )
            .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) != 0)
            .order_by(Warehouse.name, CountCatalog.count_value)
        )
        rows = result.all()
        return [
            {
                "warehouse_id": r.warehouse_id,
                "warehouse_name": r.warehouse_name,
                "count_id": r.count_id,
                "count_value": r.count_value or "",
                "owner_id": r.owner_id,
                "owner_name": r.owner_name,
                "total_kg": float(r.total_kg),
            }
            for r in rows
        ]
