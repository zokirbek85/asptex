from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raw_cotton.schemas import (
    CottonBalanceSummary,
    ProductionIssueItem,
    RawCottonStockItem,
)
from app.modules.stock.models import StockTransaction
from app.shared.enums import TransactionType


class RawCottonService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stock(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> list[RawCottonStockItem]:
        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                func.sum(
                    StockTransaction.quantity_kg * StockTransaction.direction
                ).label("total_kg"),
                func.sum(
                    StockTransaction.quantity_kip * StockTransaction.direction
                ).label("total_kip"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
            )
            .group_by(
                StockTransaction.lot_id, StockTransaction.lot_number,
                StockTransaction.count_id, StockTransaction.count_value,
                StockTransaction.owner_id, StockTransaction.owner_name,
            )
            .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0)
            .order_by(StockTransaction.lot_number, StockTransaction.owner_name)
        )
        return [
            RawCottonStockItem(
                lot_id=r.lot_id,
                lot_number=r.lot_number,
                count_id=r.count_id,
                count_value=r.count_value,
                owner_id=r.owner_id,
                owner_name=r.owner_name,
                quantity_kg=Decimal(str(r.total_kg)),
                quantity_kip=Decimal(str(r.total_kip)) if r.total_kip else None,
            )
            for r in result.all()
        ]

    async def get_production_issue_report(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ProductionIssueItem]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.transaction_type == TransactionType.PRODUCTION_ISSUE,
        ]
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                func.sum(StockTransaction.quantity_kg).label("total_kg"),
                func.count(StockTransaction.id).label("tx_count"),
            )
            .where(*conditions)
            .group_by(
                StockTransaction.lot_id, StockTransaction.lot_number,
                StockTransaction.owner_id, StockTransaction.owner_name,
            )
            .order_by(StockTransaction.lot_number)
        )
        return [
            ProductionIssueItem(
                lot_id=r.lot_id,
                lot_number=r.lot_number,
                owner_id=r.owner_id,
                owner_name=r.owner_name,
                total_kg=Decimal(str(r.total_kg)),
                transaction_count=r.tx_count,
            )
            for r in result.all()
        ]

    async def get_balance_summary(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> CottonBalanceSummary:
        items = await self.get_stock(company_id, warehouse_id)
        own = [i for i in items if i.owner_id is None]
        tolling = [i for i in items if i.owner_id is not None]
        return CottonBalanceSummary(
            own_kg=sum((i.quantity_kg for i in own), Decimal("0")),
            tolling_kg=sum((i.quantity_kg for i in tolling), Decimal("0")),
            total_kg=sum((i.quantity_kg for i in items), Decimal("0")),
            own_items=len(own),
            tolling_items=len(tolling),
        )
