from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.packaging.schemas import (
    MIN_STOCK_THRESHOLDS,
    PKG_TYPE_LABELS,
    PKG_UNIT_TYPES,
    PkgUnitType,
    MinStockAlert,
    PackagingMovementItem,
    PackagingStockItem,
)
from app.modules.stock.models import StockTransaction
from app.shared.enums import PackagingItemType, TransactionType
from app.shared.schemas import PaginatedResponse


class PackagingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stock(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> list[PackagingStockItem]:
        result = await self.session.execute(
            select(
                StockTransaction.pkg_item_type,
                func.sum(
                    StockTransaction.quantity_kg * StockTransaction.direction
                ).label("total_kg"),
                func.sum(
                    StockTransaction.quantity_units * StockTransaction.direction
                ).label("total_units"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.pkg_item_type.is_not(None),
            )
            .group_by(StockTransaction.pkg_item_type)
            .having(
                (func.coalesce(func.sum(StockTransaction.quantity_kg * StockTransaction.direction), 0) > 0) |
                (func.coalesce(func.sum(StockTransaction.quantity_units * StockTransaction.direction), 0) > 0)
            )
            .order_by(StockTransaction.pkg_item_type)
        )
        return [
            PackagingStockItem(
                pkg_item_type=r.pkg_item_type,
                display_name=PKG_TYPE_LABELS.get(r.pkg_item_type, r.pkg_item_type.value),
                unit_type=PKG_UNIT_TYPES.get(r.pkg_item_type, PkgUnitType.DONA),
                quantity_units=int(r.total_units) if r.total_units else None,
                quantity_kg=Decimal(str(r.total_kg)),
            )
            for r in result.all()
        ]

    async def get_movements(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        pkg_item_type: PackagingItemType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[PackagingMovementItem]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.pkg_item_type.is_not(None),
        ]
        if pkg_item_type is not None:
            conditions.append(StockTransaction.pkg_item_type == pkg_item_type)
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        total_result = await self.session.execute(
            select(func.count(StockTransaction.id)).where(*conditions)
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            select(StockTransaction)
            .where(*conditions)
            .order_by(StockTransaction.transaction_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        txs = list(result.scalars().all())
        items = [
            PackagingMovementItem(
                id=tx.id,
                pkg_item_type=tx.pkg_item_type,
                display_name=PKG_TYPE_LABELS.get(tx.pkg_item_type, tx.pkg_item_type.value),
                unit_type=PKG_UNIT_TYPES.get(tx.pkg_item_type, PkgUnitType.DONA),
                transaction_type=tx.transaction_type,
                direction=tx.direction,
                quantity_kg=Decimal(str(tx.quantity_kg)),
                quantity_units=tx.quantity_units,
                transaction_date=tx.transaction_date,
                posted_at=tx.posted_at,
            )
            for tx in txs
        ]
        return PaginatedResponse.build(items, total, page, page_size)

    async def get_min_stock_alerts(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> list[MinStockAlert]:
        stock_items = await self.get_stock(company_id, warehouse_id)
        stock_map = {item.pkg_item_type: item for item in stock_items}

        alerts = []
        for pkg_type in PackagingItemType:
            unit_type = PKG_UNIT_TYPES.get(pkg_type, PkgUnitType.DONA)
            threshold = MIN_STOCK_THRESHOLDS.get(pkg_type, 100)
            item = stock_map.get(pkg_type)

            if unit_type == PkgUnitType.KG:
                current_qty = float(item.quantity_kg) if item else 0.0
            else:
                if item is None or item.quantity_units is None:
                    continue
                current_qty = float(item.quantity_units)

            if current_qty < threshold:
                alerts.append(MinStockAlert(
                    pkg_item_type=pkg_type,
                    display_name=PKG_TYPE_LABELS.get(pkg_type, pkg_type.value),
                    unit_type=unit_type,
                    current_qty=current_qty,
                    min_qty=threshold,
                ))
        return alerts
