from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cotton_receiving.models import CottonReceiving
from app.modules.exchange_sale.models import ExchangeSale, ExchangeSaleLine
from app.modules.farmer_ledger.models import FarmerLedgerEntry
from app.modules.ginning_bunt.models import GinningBunt
from app.modules.ginning_dashboard.schemas import (
    ChartDataPoint,
    GinningDashboardSummary,
    GinningReceivingTrendPoint,
)
from app.modules.ginning_production.models import GinningProductionOrder, GinningProductionOutput
from app.modules.intercompany_transfer.models import IntercompanyTransfer, IntercompanyTransferLine
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.enums import (
    BuntStatus,
    CottonReceivingStatus,
    ExchangeSaleStatus,
    FarmerLedgerEntryType,
    GinningProductionStatus,
    GinningProductType,
    IntercompanyTransferStatus,
    WarehouseType,
)


class GinningDashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)

    async def get_summary(self, company_id: uuid.UUID) -> GinningDashboardSummary:
        received = await self.session.execute(
            select(func.coalesce(func.sum(CottonReceiving.net_weight_kg), 0)).where(
                CottonReceiving.company_id == company_id,
                CottonReceiving.status == CottonReceivingStatus.POSTED,
            )
        )
        raw_cotton_received_kg = Decimal(str(received.scalar_one() or 0))

        raw_wh_result = await self.session.execute(
            select(Warehouse.id).where(
                Warehouse.company_id == company_id, Warehouse.warehouse_type == WarehouseType.RAW_COTTON,
            )
        )
        raw_warehouse_ids = [row[0] for row in raw_wh_result]
        raw_cotton_available_kg = Decimal("0")
        for wh_id in raw_warehouse_ids:
            balances = await self.stock_repo.get_balances_for_warehouse(company_id, wh_id)
            raw_cotton_available_kg += sum((b["quantity_kg"] for b in balances), Decimal("0"))

        processed_result = await self.session.execute(
            select(func.coalesce(func.sum(GinningProductionOrder.total_input_kg), 0)).where(
                GinningProductionOrder.company_id == company_id,
                GinningProductionOrder.status == GinningProductionStatus.COMPLETED,
            )
        )
        raw_cotton_processed_kg = Decimal(str(processed_result.scalar_one() or 0))

        output_by_product = await self.session.execute(
            select(GinningProductionOutput.product_type, func.coalesce(func.sum(GinningProductionOutput.quantity_kg), 0))
            .join(GinningProductionOrder, GinningProductionOutput.order_id == GinningProductionOrder.id)
            .where(
                GinningProductionOrder.company_id == company_id,
                GinningProductionOrder.status == GinningProductionStatus.COMPLETED,
            )
            .group_by(GinningProductionOutput.product_type)
        )
        output_map = {row[0]: Decimal(str(row[1])) for row in output_by_product}
        fiber = output_map.get(GinningProductType.FIBER, Decimal("0"))
        seed = output_map.get(GinningProductType.SEED, Decimal("0"))
        lint = output_map.get(GinningProductType.LINT, Decimal("0"))
        pux = output_map.get(GinningProductType.PUX, Decimal("0"))
        ulyuk = output_map.get(GinningProductType.ULYUK, Decimal("0"))
        total_output = sum(output_map.values(), Decimal("0"))
        fiber_yield_pct = (fiber / raw_cotton_processed_kg * 100) if raw_cotton_processed_kg > 0 else Decimal("0")

        sales_result = await self.session.execute(
            select(
                func.coalesce(func.sum((ExchangeSaleLine.quantity_kg - ExchangeSaleLine.cancelled_kg) * ExchangeSaleLine.unit_price), 0),
                func.coalesce(func.sum(ExchangeSaleLine.quantity_kg - ExchangeSaleLine.cancelled_kg), 0),
            )
            .join(ExchangeSale, ExchangeSaleLine.sale_id == ExchangeSale.id)
            .where(ExchangeSale.company_id == company_id, ExchangeSale.status != ExchangeSaleStatus.CANCELLED)
        )
        sales_row = sales_result.one()
        exchange_sales_value = Decimal(str(sales_row[0] or 0))
        exchange_sales_kg = Decimal(str(sales_row[1] or 0))

        transfer_result = await self.session.execute(
            select(func.coalesce(func.sum(IntercompanyTransferLine.quantity_kg), 0))
            .join(IntercompanyTransfer, IntercompanyTransferLine.transfer_id == IntercompanyTransfer.id)
            .where(
                IntercompanyTransfer.source_company_id == company_id,
                IntercompanyTransfer.status == IntercompanyTransferStatus.CONFIRMED,
            )
        )
        intercompany_transfers_kg = Decimal(str(transfer_result.scalar_one() or 0))

        farmer_balances = await self.session.execute(
            select(FarmerLedgerEntry.farmer_id, func.sum(FarmerLedgerEntry.amount * FarmerLedgerEntry.direction))
            .where(FarmerLedgerEntry.company_id == company_id)
            .group_by(FarmerLedgerEntry.farmer_id)
        )
        farmer_payable_total = sum(
            (Decimal(str(bal)) for _, bal in farmer_balances if bal and Decimal(str(bal)) > 0), Decimal("0")
        )
        paid_result = await self.session.execute(
            select(func.coalesce(func.sum(FarmerLedgerEntry.amount), 0)).where(
                FarmerLedgerEntry.company_id == company_id,
                FarmerLedgerEntry.entry_type == FarmerLedgerEntryType.PAYMENT,
            )
        )
        farmer_paid_total = Decimal(str(paid_result.scalar_one() or 0))

        open_bunts_result = await self.session.execute(
            select(func.count(GinningBunt.id)).where(
                GinningBunt.company_id == company_id, GinningBunt.status == BuntStatus.OPEN,
            )
        )
        open_bunts_count = open_bunts_result.scalar_one() or 0

        draft_orders_result = await self.session.execute(
            select(func.count(GinningProductionOrder.id)).where(
                GinningProductionOrder.company_id == company_id,
                GinningProductionOrder.status == GinningProductionStatus.DRAFT,
            )
        )
        draft_production_orders_count = draft_orders_result.scalar_one() or 0

        return GinningDashboardSummary(
            raw_cotton_received_kg=raw_cotton_received_kg,
            raw_cotton_available_kg=raw_cotton_available_kg,
            raw_cotton_processed_kg=raw_cotton_processed_kg,
            fiber_produced_kg=fiber,
            seed_produced_kg=seed,
            lint_produced_kg=lint,
            pux_produced_kg=pux,
            ulyuk_produced_kg=ulyuk,
            total_output_kg=total_output,
            fiber_yield_pct=fiber_yield_pct,
            exchange_sales_value=exchange_sales_value,
            exchange_sales_kg=exchange_sales_kg,
            intercompany_transfers_kg=intercompany_transfers_kg,
            farmer_payable_total=farmer_payable_total,
            farmer_paid_total=farmer_paid_total,
            open_bunts_count=open_bunts_count,
            draft_production_orders_count=draft_production_orders_count,
        )

    async def get_receiving_trend(self, company_id: uuid.UUID, days: int = 30) -> list[GinningReceivingTrendPoint]:
        result = await self.session.execute(
            select(CottonReceiving.receiving_date, func.sum(CottonReceiving.net_weight_kg))
            .where(
                CottonReceiving.company_id == company_id,
                CottonReceiving.status == CottonReceivingStatus.POSTED,
            )
            .group_by(CottonReceiving.receiving_date)
            .order_by(CottonReceiving.receiving_date.desc())
            .limit(days)
        )
        rows = result.all()
        return [
            GinningReceivingTrendPoint(date=row[0], quantity_kg=Decimal(str(row[1])))
            for row in sorted(rows, key=lambda r: r[0])
        ]

    async def get_output_distribution(self, company_id: uuid.UUID) -> list[ChartDataPoint]:
        result = await self.session.execute(
            select(GinningProductionOutput.product_type, func.sum(GinningProductionOutput.quantity_kg))
            .join(GinningProductionOrder, GinningProductionOutput.order_id == GinningProductionOrder.id)
            .where(
                GinningProductionOrder.company_id == company_id,
                GinningProductionOrder.status == GinningProductionStatus.COMPLETED,
            )
            .group_by(GinningProductionOutput.product_type)
        )
        return [ChartDataPoint(label=row[0].value, value=Decimal(str(row[1]))) for row in result]
