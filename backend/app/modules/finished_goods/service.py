from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finished_goods.schemas import (
    FinishedGoodsStockItem,
    LotStockBreakdown,
    ProductionReportItem,
    ShipmentReportItem,
)
from app.modules.lot.models import Lot
from app.modules.stock.models import StockTransaction
from app.modules.stock.repository import StockRepository
from app.shared.enums import LotStatus, TransactionType, WarehouseType


class FinishedGoodsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)

    async def _get_finished_goods_warehouse_ids(
        self, company_id: uuid.UUID
    ) -> list[uuid.UUID]:
        from app.modules.warehouse.models import Warehouse
        result = await self.session.execute(
            select(Warehouse.id).where(
                Warehouse.company_id == company_id,
                Warehouse.warehouse_type == WarehouseType.FINISHED_GOODS,
                Warehouse.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_stock(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        lot_id: uuid.UUID | None = None,
        count_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        lot_status: LotStatus | None = None,
    ) -> list[FinishedGoodsStockItem]:
        balance_expr = func.sum(
            StockTransaction.quantity_kg * StockTransaction.direction
        ).label("total_kg")
        bags_expr = func.sum(
            StockTransaction.quantity_bags * StockTransaction.direction
        ).label("total_bags")

        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.lot_id.is_not(None),
        ]
        if lot_id is not None:
            conditions.append(StockTransaction.lot_id == lot_id)
        if count_id is not None:
            conditions.append(StockTransaction.count_id == count_id)
        if owner_id is not None:
            conditions.append(StockTransaction.owner_id == owner_id)

        stmt = (
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                balance_expr,
                bags_expr,
            )
            .where(*conditions)
            .group_by(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
            )
            .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0)
            .order_by(StockTransaction.lot_number, StockTransaction.count_value)
        )

        if lot_status is not None:
            stmt = stmt.join(Lot, Lot.id == StockTransaction.lot_id).where(
                Lot.status == lot_status
            )

        result = await self.session.execute(stmt)
        rows = result.all()

        lot_statuses: dict[uuid.UUID, LotStatus] = {}
        lot_numbers: dict[uuid.UUID, str] = {}
        if rows:
            lot_ids = list({r.lot_id for r in rows if r.lot_id})
            lots_result = await self.session.execute(
                select(Lot.id, Lot.status, Lot.lot_number).where(Lot.id.in_(lot_ids))
            )
            for lot_row in lots_result.all():
                lot_statuses[lot_row.id] = lot_row.status
                lot_numbers[lot_row.id] = lot_row.lot_number

        return [
            FinishedGoodsStockItem(
                lot_id=r.lot_id,
                lot_number=r.lot_number or lot_numbers.get(r.lot_id, ""),
                lot_status=lot_statuses.get(r.lot_id, LotStatus.OPEN),
                count_id=r.count_id,
                count_value=r.count_value,
                owner_id=r.owner_id,
                owner_name=r.owner_name,
                quantity_kg=Decimal(str(r.total_kg)),
                quantity_bags=int(r.total_bags) if r.total_bags else None,
            )
            for r in rows
        ]

    async def get_lot_breakdown(
        self, company_id: uuid.UUID, warehouse_id: uuid.UUID, lot_id: uuid.UUID
    ) -> LotStockBreakdown:
        lot_result = await self.session.execute(select(Lot).where(Lot.id == lot_id))
        lot = lot_result.scalar_one_or_none()
        items = await self.get_stock(company_id, warehouse_id, lot_id=lot_id)
        total_kg = sum((i.quantity_kg for i in items), Decimal("0"))
        return LotStockBreakdown(
            lot_id=lot_id,
            lot_number=lot.lot_number if lot else "",
            lot_status=lot.status if lot else LotStatus.OPEN,
            items=items,
            total_kg=total_kg,
        )

    async def get_production_report(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ProductionReportItem]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.transaction_type == TransactionType.PRODUCTION_INBOUND,
        ]
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                func.sum(StockTransaction.quantity_kg).label("total_kg"),
                func.count(StockTransaction.id).label("tx_count"),
            )
            .where(*conditions)
            .group_by(
                StockTransaction.lot_id, StockTransaction.lot_number,
                StockTransaction.count_id, StockTransaction.count_value,
                StockTransaction.owner_id, StockTransaction.owner_name,
            )
            .order_by(StockTransaction.lot_number)
        )
        return [
            ProductionReportItem(
                lot_id=r.lot_id,
                lot_number=r.lot_number or "",
                count_id=r.count_id,
                count_value=r.count_value,
                owner_id=r.owner_id,
                owner_name=r.owner_name,
                total_kg=Decimal(str(r.total_kg)),
                transaction_count=r.tx_count,
            )
            for r in result.all()
        ]

    async def get_shipment_report(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShipmentReportItem]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
            StockTransaction.transaction_type == TransactionType.SHIPMENT_OUTBOUND,
        ]
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        result = await self.session.execute(
            select(
                StockTransaction.owner_id.label("buyer_id"),
                StockTransaction.owner_name.label("buyer_name"),
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                func.sum(StockTransaction.quantity_kg).label("total_kg"),
                func.count(StockTransaction.id).label("tx_count"),
            )
            .where(*conditions)
            .group_by(
                StockTransaction.owner_id, StockTransaction.owner_name,
                StockTransaction.lot_id, StockTransaction.lot_number,
                StockTransaction.count_id, StockTransaction.count_value,
            )
            .order_by(StockTransaction.owner_name, StockTransaction.lot_number)
        )
        return [
            ShipmentReportItem(
                buyer_id=r.buyer_id,
                buyer_name=r.buyer_name,
                lot_id=r.lot_id,
                lot_number=r.lot_number or "",
                count_id=r.count_id,
                count_value=r.count_value,
                total_kg=Decimal(str(r.total_kg)),
                transaction_count=r.tx_count,
            )
            for r in result.all()
        ]
