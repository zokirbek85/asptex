from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stock.models import StockTransaction
from app.modules.waste.schemas import (
    WASTE_TYPE_LABELS,
    WasteMovementItem,
    WasteStockItem,
    WasteSalesReportItem,
)
from app.shared.enums import TransactionType, WasteType
from app.shared.schemas import PaginatedResponse


class WasteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stock(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> list[WasteStockItem]:
        result = await self.session.execute(
            select(
                StockTransaction.waste_type,
                func.sum(
                    StockTransaction.quantity_kg * StockTransaction.direction
                ).label("total_kg"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.waste_type.is_not(None),
            )
            .group_by(StockTransaction.waste_type)
            .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0)
            .order_by(StockTransaction.waste_type)
        )
        return [
            WasteStockItem(
                waste_type=r.waste_type,
                display_name=WASTE_TYPE_LABELS.get(r.waste_type, r.waste_type.value),
                quantity_kg=Decimal(str(r.total_kg)),
            )
            for r in result.all()
        ]

    async def get_movements(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        waste_type: WasteType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        transaction_type: TransactionType | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[WasteMovementItem]:
        from sqlalchemy import func as sqlfunc
        from app.shared.base_repository import BaseRepository

        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.waste_type.is_not(None),
        ]
        if waste_type is not None:
            conditions.append(StockTransaction.waste_type == waste_type)
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)
        if transaction_type is not None:
            conditions.append(StockTransaction.transaction_type == transaction_type)

        total_result = await self.session.execute(
            select(sqlfunc.count(StockTransaction.id)).where(*conditions)
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            select(StockTransaction)
            .where(*conditions)
            .order_by(StockTransaction.transaction_date.desc(), StockTransaction.posted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        txs = list(result.scalars().all())
        items = [
            WasteMovementItem(
                id=tx.id,
                waste_type=tx.waste_type,
                display_name=WASTE_TYPE_LABELS.get(tx.waste_type, tx.waste_type.value),
                transaction_type=tx.transaction_type,
                direction=tx.direction,
                quantity_kg=Decimal(str(tx.quantity_kg)),
                owner_name=tx.owner_name,
                transaction_date=tx.transaction_date,
                posted_at=tx.posted_at,
            )
            for tx in txs
        ]
        return PaginatedResponse.build(items, total, page, page_size)

    async def get_sales_report(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[WasteSalesReportItem]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.transaction_type == TransactionType.WASTE_SALE_OUTBOUND,
        ]
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        result = await self.session.execute(
            select(
                StockTransaction.owner_id.label("buyer_id"),
                StockTransaction.owner_name.label("buyer_name"),
                StockTransaction.waste_type,
                func.sum(StockTransaction.quantity_kg).label("total_kg"),
                func.count(StockTransaction.id).label("tx_count"),
            )
            .where(*conditions)
            .group_by(
                StockTransaction.owner_id, StockTransaction.owner_name,
                StockTransaction.waste_type,
            )
            .order_by(StockTransaction.owner_name, StockTransaction.waste_type)
        )
        return [
            WasteSalesReportItem(
                buyer_id=r.buyer_id,
                buyer_name=r.buyer_name,
                waste_type=r.waste_type,
                display_name=WASTE_TYPE_LABELS.get(r.waste_type, r.waste_type.value),
                total_kg=Decimal(str(r.total_kg)),
                transaction_count=r.tx_count,
            )
            for r in result.all()
        ]
