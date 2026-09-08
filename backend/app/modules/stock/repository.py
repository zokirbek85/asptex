from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stock.models import StockTransaction
from app.shared.base_repository import BaseRepository
from app.shared.enums import GinningProductType, PackagingItemType, TransactionType, WasteType


class StockRepository(BaseRepository[StockTransaction]):
    model = StockTransaction

    async def get_balance(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        lot_id: uuid.UUID | None = None,
        count_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        waste_type: WasteType | None = None,
        pkg_item_type: PackagingItemType | None = None,
        ginning_product_type: GinningProductType | None = None,
    ) -> Decimal:
        """Returns SUM(quantity_kg * direction). Always exact-matches all identity dims (None → IS NULL)."""
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
        ]

        if lot_id is not None:
            conditions.append(StockTransaction.lot_id == lot_id)
        else:
            conditions.append(StockTransaction.lot_id.is_(None))

        if count_id is not None:
            conditions.append(StockTransaction.count_id == count_id)
        else:
            conditions.append(StockTransaction.count_id.is_(None))

        if owner_id is not None:
            conditions.append(StockTransaction.owner_id == owner_id)
        else:
            conditions.append(StockTransaction.owner_id.is_(None))

        if waste_type is not None:
            conditions.append(StockTransaction.waste_type == waste_type)
        else:
            conditions.append(StockTransaction.waste_type.is_(None))

        if pkg_item_type is not None:
            conditions.append(StockTransaction.pkg_item_type == pkg_item_type)
        else:
            conditions.append(StockTransaction.pkg_item_type.is_(None))

        if ginning_product_type is not None:
            conditions.append(StockTransaction.ginning_product_type == ginning_product_type)
        else:
            conditions.append(StockTransaction.ginning_product_type.is_(None))

        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(StockTransaction.quantity_kg * StockTransaction.direction),
                    0,
                ).label("balance")
            ).where(*conditions)
        )
        val = result.scalar_one()
        return Decimal(str(val)) if val is not None else Decimal("0")

    async def get_balances_for_warehouse(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> list[dict]:
        """GROUP BY all identity dims, returns rows with balance > 0."""
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
        ]
        if as_of_date is not None:
            conditions.append(StockTransaction.transaction_date <= as_of_date)

        balance_expr = func.sum(
            StockTransaction.quantity_kg * StockTransaction.direction
        ).label("balance")

        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
                StockTransaction.ginning_product_type,
                balance_expr,
                func.sum(StockTransaction.quantity_bags).label("total_bags"),
                func.sum(StockTransaction.quantity_units).label("total_units"),
            )
            .where(*conditions)
            .group_by(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.count_id,
                StockTransaction.count_value,
                StockTransaction.owner_id,
                StockTransaction.owner_name,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
                StockTransaction.ginning_product_type,
            )
            .having(
                func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0
            )
            .order_by(StockTransaction.lot_number, StockTransaction.count_value)
        )
        rows = result.all()
        return [
            {
                "lot_id": r.lot_id,
                "lot_number": r.lot_number,
                "count_id": r.count_id,
                "count_value": r.count_value,
                "owner_id": r.owner_id,
                "owner_name": r.owner_name,
                "waste_type": r.waste_type,
                "pkg_item_type": r.pkg_item_type,
                "ginning_product_type": r.ginning_product_type,
                "quantity_kg": Decimal(str(r.balance)),
                "quantity_bags": int(r.total_bags) if r.total_bags else None,
                "quantity_units": int(r.total_units) if r.total_units else None,
            }
            for r in rows
        ]

    async def get_transactions(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        lot_id: uuid.UUID | None = None,
        count_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        reference_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[StockTransaction], int]:
        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.warehouse_id == warehouse_id,
        ]
        if lot_id is not None:
            conditions.append(StockTransaction.lot_id == lot_id)
        if count_id is not None:
            conditions.append(StockTransaction.count_id == count_id)
        if owner_id is not None:
            conditions.append(StockTransaction.owner_id == owner_id)
        if date_from is not None:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to is not None:
            conditions.append(StockTransaction.transaction_date <= date_to)
        if reference_type is not None:
            conditions.append(StockTransaction.reference_type == reference_type)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(StockTransaction)
            .where(*conditions)
            .order_by(StockTransaction.transaction_date.desc(), StockTransaction.posted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def post_transaction(
        self,
        *,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        transaction_type: TransactionType,
        direction: int,
        quantity_kg: Decimal,
        transaction_date: date,
        posted_by: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
        reference_line_id: uuid.UUID | None = None,
        lot_id: uuid.UUID | None = None,
        count_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        waste_type: WasteType | None = None,
        pkg_item_type: PackagingItemType | None = None,
        ginning_product_type: GinningProductType | None = None,
        quantity_bags: int | None = None,
        quantity_kip: Decimal | None = None,
        quantity_units: int | None = None,
        lot_number: str | None = None,
        count_value: str | None = None,
        owner_name: str | None = None,
        notes: str | None = None,
    ) -> StockTransaction:
        tx = StockTransaction(
            company_id=company_id,
            warehouse_id=warehouse_id,
            transaction_type=transaction_type,
            direction=direction,
            quantity_kg=quantity_kg,
            transaction_date=transaction_date,
            posted_by=posted_by,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_line_id=reference_line_id,
            lot_id=lot_id,
            count_id=count_id,
            owner_id=owner_id,
            waste_type=waste_type,
            pkg_item_type=pkg_item_type,
            ginning_product_type=ginning_product_type,
            quantity_bags=quantity_bags,
            quantity_kip=quantity_kip,
            quantity_units=quantity_units,
            lot_number=lot_number,
            count_value=count_value,
            owner_name=owner_name,
            notes=notes,
        )
        self.session.add(tx)
        await self.session.flush()
        await self.session.refresh(tx)
        return tx

    async def get_tolling_raw_actual(
        self,
        company_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Decimal:
        """Sum of TOLLING_RAW_RECEIPT inbound for a given tolling owner (all lots)."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(StockTransaction.quantity_kg), 0)
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.transaction_type == TransactionType.TOLLING_RAW_RECEIPT,
                StockTransaction.owner_id == owner_id,
                StockTransaction.direction == 1,
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def get_tolling_fg_shipped(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        lot_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Decimal:
        """Sum of SHIPMENT_OUTBOUND kg for a tolling owner in a specific FG lot."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(StockTransaction.quantity_kg), 0)
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.lot_id == lot_id,
                StockTransaction.owner_id == owner_id,
                StockTransaction.transaction_type == TransactionType.SHIPMENT_OUTBOUND,
                StockTransaction.direction == -1,
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def get_tolling_raw_actual_batch(
        self,
        company_id: uuid.UUID,
        owner_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Decimal]:
        """Batched form of get_tolling_raw_actual — one query for all owners."""
        if not owner_ids:
            return {}
        result = await self.session.execute(
            select(
                StockTransaction.owner_id,
                func.coalesce(func.sum(StockTransaction.quantity_kg), 0),
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.transaction_type == TransactionType.TOLLING_RAW_RECEIPT,
                StockTransaction.owner_id.in_(owner_ids),
                StockTransaction.direction == 1,
            ).group_by(StockTransaction.owner_id)
        )
        return {row[0]: Decimal(str(row[1])) for row in result}

    async def get_tolling_fg_shipped_batch(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        lot_ids: list[uuid.UUID],
        owner_ids: list[uuid.UUID],
    ) -> dict[tuple[uuid.UUID, uuid.UUID], Decimal]:
        """Batched form of get_tolling_fg_shipped — one query for all (lot, owner) pairs."""
        if not lot_ids or not owner_ids:
            return {}
        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.owner_id,
                func.coalesce(func.sum(StockTransaction.quantity_kg), 0),
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.lot_id.in_(lot_ids),
                StockTransaction.owner_id.in_(owner_ids),
                StockTransaction.transaction_type == TransactionType.SHIPMENT_OUTBOUND,
                StockTransaction.direction == -1,
            ).group_by(StockTransaction.lot_id, StockTransaction.owner_id)
        )
        return {(row[0], row[1]): Decimal(str(row[2])) for row in result}

    async def get_slow_stock_lots(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        days: int = 60,
    ) -> list[dict]:
        """Returns identity groups with last_movement_date and current balance."""
        from datetime import datetime, timezone, timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()

        balance_expr = func.sum(
            StockTransaction.quantity_kg * StockTransaction.direction
        ).label("balance")
        last_movement = func.max(StockTransaction.transaction_date).label("last_movement_date")

        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
                StockTransaction.ginning_product_type,
                balance_expr,
                last_movement,
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
            )
            .group_by(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
                StockTransaction.ginning_product_type,
            )
            .having(
                func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0,
                func.max(StockTransaction.transaction_date) < cutoff,
            )
            .order_by(last_movement)
        )
        rows = result.all()
        return [
            {
                "lot_id": r.lot_id,
                "lot_number": r.lot_number,
                "waste_type": r.waste_type,
                "pkg_item_type": r.pkg_item_type,
                "ginning_product_type": r.ginning_product_type,
                "quantity_kg": Decimal(str(r.balance)),
                "last_movement_date": r.last_movement_date,
            }
            for r in rows
        ]
