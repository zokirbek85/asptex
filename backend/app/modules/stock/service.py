from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NegativeStockBlockedError
from app.modules.stock.repository import StockRepository
from app.shared.enums import GinningProductType, PackagingItemType, WasteType


class StockService:
    """Orchestrates stock posting. Called by DailyReportService, ShipmentService, AdjustmentService."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StockRepository(session)

    async def check_balance_and_warn(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        delta_kg: Decimal,
        lot_id: uuid.UUID | None = None,
        count_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        waste_type: WasteType | None = None,
        pkg_item_type: PackagingItemType | None = None,
        ginning_product_type: GinningProductType | None = None,
        lot_number: str | None = None,
        owner_name: str | None = None,
    ) -> tuple[Decimal, bool]:
        """
        Returns (current_balance, would_go_negative).
        Owner-level finished goods negative → raises NegativeStockBlockedError (BLOCK).
        All other negatives → returns True flag without raising (WARNING).
        """
        current = await self.repo.get_balance(
            company_id=company_id,
            warehouse_id=warehouse_id,
            lot_id=lot_id,
            count_id=count_id,
            owner_id=owner_id,
            waste_type=waste_type,
            pkg_item_type=pkg_item_type,
            ginning_product_type=ginning_product_type,
        )
        after = current + delta_kg
        would_go_negative = after < Decimal("0")

        if would_go_negative and lot_id is not None and owner_id is not None:
            # Finished goods with explicit owner — BLOCK
            raise NegativeStockBlockedError(
                lot_number=lot_number,
                owner_name=owner_name,
            )

        return current, would_go_negative

    async def get_slow_stock_lots(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        days: int = 60,
    ) -> list[dict]:
        return await self.repo.get_slow_stock_lots(company_id, warehouse_id, days)
