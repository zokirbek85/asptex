from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.adjustment.models import InventoryAdjustment
from app.modules.daily_report.models import DailyReport
from app.modules.lot.models import Lot
from app.modules.shipment.models import Shipment, ShipmentLine
from app.modules.stock.models import StockTransaction
from app.modules.warehouse.models import Warehouse
from app.modules.dashboard.schemas import (
    ChartDataPoint,
    DashboardAlert,
    DashboardSummary,
    SlowStockItem,
    StockByLot,
    UnclosedReportItem,
)
from app.modules.waste.schemas import WASTE_TYPE_LABELS
from app.modules.packaging.schemas import PKG_TYPE_LABELS
from app.shared.enums import (
    AdjustmentStatus,
    LotStatus,
    ReportStatus,
    TransactionType,
    WarehouseType,
)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_warehouse_ids(
        self, company_id: uuid.UUID, warehouse_type: WarehouseType
    ) -> list[uuid.UUID]:
        result = await self.session.execute(
            select(Warehouse.id).where(
                Warehouse.company_id == company_id,
                Warehouse.warehouse_type == warehouse_type,
                Warehouse.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def _total_stock_kg(
        self, company_id: uuid.UUID, warehouse_type: WarehouseType
    ) -> Decimal:
        wh_ids = await self._get_warehouse_ids(company_id, warehouse_type)
        if not wh_ids:
            return Decimal("0")
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(StockTransaction.quantity_kg * StockTransaction.direction), 0
                )
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id.in_(wh_ids),
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def _total_packaging_units(self, company_id: uuid.UUID) -> int:
        wh_ids = await self._get_warehouse_ids(company_id, WarehouseType.PACKAGING)
        if not wh_ids:
            return 0
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(StockTransaction.quantity_units * StockTransaction.direction), 0
                )
            ).where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id.in_(wh_ids),
            )
        )
        return int(result.scalar_one() or 0)

    async def get_summary(self, company_id: uuid.UUID) -> DashboardSummary:
        today = datetime.now(timezone.utc).date()
        month_start = today.replace(day=1)

        fg_kg = await self._total_stock_kg(company_id, WarehouseType.FINISHED_GOODS)
        rc_kg = await self._total_stock_kg(company_id, WarehouseType.RAW_COTTON)
        waste_kg = await self._total_stock_kg(company_id, WarehouseType.WASTE)
        pkg_units = await self._total_packaging_units(company_id)

        # Shipments this month
        ship_result = await self.session.execute(
            select(
                func.count(Shipment.id).label("cnt"),
                func.coalesce(func.sum(ShipmentLine.quantity_kg), 0).label("total_kg"),
            )
            .join(ShipmentLine, ShipmentLine.shipment_id == Shipment.id, isouter=True)
            .where(
                Shipment.company_id == company_id,
                Shipment.shipment_date >= month_start,
            )
        )
        ship_row = ship_result.one()

        # Active lots with stock
        active_lots_result = await self.session.execute(
            select(func.count(Lot.id)).where(
                Lot.company_id == company_id,
                Lot.status == LotStatus.OPEN,
            )
        )
        active_lots = active_lots_result.scalar_one() or 0

        # Open daily reports
        open_reports_result = await self.session.execute(
            select(func.count(DailyReport.id)).where(
                DailyReport.company_id == company_id,
                DailyReport.status.in_([ReportStatus.DRAFT, ReportStatus.SUBMITTED]),
            )
        )
        open_reports = open_reports_result.scalar_one() or 0

        # Slow stock count
        cutoff = today - timedelta(days=60)
        all_wh_result = await self.session.execute(
            select(Warehouse.id).where(
                Warehouse.company_id == company_id, Warehouse.is_active == True
            )
        )
        all_wh_ids = list(all_wh_result.scalars().all())

        slow_count = 0
        if all_wh_ids:
            slow_result = await self.session.execute(
                select(func.count()).select_from(
                    select(
                        StockTransaction.lot_id,
                        StockTransaction.waste_type,
                        StockTransaction.pkg_item_type,
                    )
                    .where(
                        StockTransaction.company_id == company_id,
                        StockTransaction.warehouse_id.in_(all_wh_ids),
                    )
                    .group_by(
                        StockTransaction.lot_id,
                        StockTransaction.waste_type,
                        StockTransaction.pkg_item_type,
                    )
                    .having(
                        func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0,
                        func.max(StockTransaction.transaction_date) < cutoff,
                    )
                    .subquery()
                )
            )
            slow_count = slow_result.scalar_one() or 0

        # Pending adjustments
        pending_adj_result = await self.session.execute(
            select(func.count(InventoryAdjustment.id)).where(
                InventoryAdjustment.company_id == company_id,
                InventoryAdjustment.status == AdjustmentStatus.DRAFT,
            )
        )
        pending_adj = pending_adj_result.scalar_one() or 0

        return DashboardSummary(
            finished_goods_kg=fg_kg,
            raw_cotton_kg=rc_kg,
            waste_kg=waste_kg,
            packaging_units=pkg_units,
            shipments_this_month=ship_row.cnt,
            shipments_kg_this_month=Decimal(str(ship_row.total_kg)),
            active_lots=active_lots,
            open_daily_reports=open_reports,
            slow_stock_count=slow_count,
            pending_adjustments=pending_adj,
        )

    async def get_fg_chart(self, company_id: uuid.UUID) -> dict[str, list[ChartDataPoint]]:
        wh_ids = await self._get_warehouse_ids(company_id, WarehouseType.FINISHED_GOODS)
        today = datetime.now(timezone.utc).date()
        date_from = today - timedelta(days=29)

        production: list[ChartDataPoint] = []
        shipments: list[ChartDataPoint] = []

        if wh_ids:
            result = await self.session.execute(
                select(
                    StockTransaction.transaction_date,
                    StockTransaction.transaction_type,
                    func.sum(StockTransaction.quantity_kg).label("total_kg"),
                )
                .where(
                    StockTransaction.company_id == company_id,
                    StockTransaction.warehouse_id.in_(wh_ids),
                    StockTransaction.transaction_date >= date_from,
                    StockTransaction.transaction_type.in_([
                        TransactionType.PRODUCTION_INBOUND,
                        TransactionType.SHIPMENT_OUTBOUND,
                    ]),
                )
                .group_by(
                    StockTransaction.transaction_date,
                    StockTransaction.transaction_type,
                )
                .order_by(StockTransaction.transaction_date)
            )
            rows = result.all()
            prod_map: dict[date, Decimal] = {}
            ship_map: dict[date, Decimal] = {}
            for r in rows:
                if r.transaction_type == TransactionType.PRODUCTION_INBOUND:
                    prod_map[r.transaction_date] = Decimal(str(r.total_kg))
                else:
                    ship_map[r.transaction_date] = Decimal(str(r.total_kg))

            for i in range(30):
                d = date_from + timedelta(days=i)
                production.append(ChartDataPoint(date=d, value=prod_map.get(d, Decimal("0"))))
                shipments.append(ChartDataPoint(date=d, value=ship_map.get(d, Decimal("0"))))

        return {"production": production, "shipments": shipments}

    async def get_stock_by_lot(self, company_id: uuid.UUID) -> list[StockByLot]:
        wh_ids = await self._get_warehouse_ids(company_id, WarehouseType.FINISHED_GOODS)
        if not wh_ids:
            return []

        result = await self.session.execute(
            select(
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                func.sum(StockTransaction.quantity_kg * StockTransaction.direction).label("total_kg"),
                func.sum(StockTransaction.quantity_bags * StockTransaction.direction).label("total_bags"),
                func.count(func.distinct(StockTransaction.owner_id)).label("owner_count"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id.in_(wh_ids),
                StockTransaction.lot_id.is_not(None),
            )
            .group_by(StockTransaction.lot_id, StockTransaction.lot_number)
            .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0)
            .order_by(func.sum(StockTransaction.quantity_kg * StockTransaction.direction).desc())
            .limit(20)
        )
        rows = result.all()

        if not rows:
            return []

        lot_ids = [r.lot_id for r in rows]
        lot_statuses_result = await self.session.execute(
            select(Lot.id, Lot.status).where(Lot.id.in_(lot_ids))
        )
        statuses = {r.id: r.status for r in lot_statuses_result.all()}

        return [
            StockByLot(
                lot_id=r.lot_id,
                lot_number=r.lot_number or "",
                status=statuses.get(r.lot_id, LotStatus.OPEN),
                total_kg=Decimal(str(r.total_kg)),
                total_bags=int(r.total_bags) if r.total_bags else 0,
                owners=r.owner_count,
            )
            for r in rows
        ]

    async def get_slow_stock(self, company_id: uuid.UUID) -> list[SlowStockItem]:
        today = datetime.now(timezone.utc).date()
        cutoff = today - timedelta(days=60)

        all_wh_result = await self.session.execute(
            select(Warehouse.id, Warehouse.warehouse_type).where(
                Warehouse.company_id == company_id, Warehouse.is_active == True
            )
        )
        wh_map = {r.id: r.warehouse_type for r in all_wh_result.all()}
        if not wh_map:
            return []

        result = await self.session.execute(
            select(
                StockTransaction.warehouse_id,
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
                func.sum(StockTransaction.quantity_kg * StockTransaction.direction).label("balance"),
                func.max(StockTransaction.transaction_date).label("last_move"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id.in_(list(wh_map.keys())),
            )
            .group_by(
                StockTransaction.warehouse_id,
                StockTransaction.lot_id,
                StockTransaction.lot_number,
                StockTransaction.waste_type,
                StockTransaction.pkg_item_type,
            )
            .having(
                func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0,
                func.max(StockTransaction.transaction_date) < cutoff,
            )
            .order_by(func.max(StockTransaction.transaction_date))
            .limit(50)
        )

        items = []
        for r in result.all():
            wh_type = wh_map.get(r.warehouse_id, WarehouseType.FINISHED_GOODS)
            if r.waste_type:
                identifier = WASTE_TYPE_LABELS.get(r.waste_type, r.waste_type.value)
            elif r.pkg_item_type:
                identifier = PKG_TYPE_LABELS.get(r.pkg_item_type, r.pkg_item_type.value)
            else:
                identifier = r.lot_number or str(r.lot_id)

            days_idle = (today - r.last_move).days if r.last_move else 999
            items.append(SlowStockItem(
                warehouse_type=wh_type,
                identifier=identifier,
                quantity_kg=Decimal(str(r.balance)),
                last_movement_date=r.last_move,
                days_idle=days_idle,
            ))
        return items

    async def get_recent_shipments(self, company_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(Shipment)
            .where(Shipment.company_id == company_id)
            .order_by(Shipment.created_at.desc())
            .limit(10)
        )
        shipments = list(result.scalars().all())
        out = []
        for s in shipments:
            total_kg_result = await self.session.execute(
                select(func.sum(ShipmentLine.quantity_kg)).where(
                    ShipmentLine.shipment_id == s.id
                )
            )
            total_kg = Decimal(str(total_kg_result.scalar_one() or 0))
            out.append({
                "id": s.id,
                "shipment_number": s.shipment_number,
                "shipment_date": s.shipment_date,
                "buyer_id": s.buyer_id,
                "status": s.status,
                "total_kg": total_kg,
            })
        return out

    async def get_unclosed_reports(self, company_id: uuid.UUID) -> list[UnclosedReportItem]:
        result = await self.session.execute(
            select(
                DailyReport.id,
                DailyReport.report_date,
                DailyReport.warehouse_id,
                DailyReport.status,
                Warehouse.name.label("warehouse_name"),
            )
            .join(Warehouse, Warehouse.id == DailyReport.warehouse_id)
            .where(
                DailyReport.company_id == company_id,
                DailyReport.status.in_([ReportStatus.DRAFT, ReportStatus.SUBMITTED]),
            )
            .order_by(DailyReport.report_date.asc())
        )
        return [
            UnclosedReportItem(
                id=r.id,
                report_date=r.report_date,
                warehouse_id=r.warehouse_id,
                warehouse_name=r.warehouse_name,
                status=r.status.value,
            )
            for r in result.all()
        ]

    async def get_alerts(self, company_id: uuid.UUID) -> list[DashboardAlert]:
        alerts: list[DashboardAlert] = []

        summary = await self.get_summary(company_id)

        if summary.slow_stock_count > 0:
            alerts.append(DashboardAlert(
                alert_type="SLOW_STOCK",
                severity="WARNING",
                message=f"{summary.slow_stock_count} ta mahsulot 60+ kun harakatsiz",
            ))

        if summary.pending_adjustments > 0:
            alerts.append(DashboardAlert(
                alert_type="OPEN_ADJUSTMENT",
                severity="WARNING",
                message=f"{summary.pending_adjustments} ta korrektura kutilmoqda (DRAFT)",
            ))

        if summary.open_daily_reports > 0:
            alerts.append(DashboardAlert(
                alert_type="UNCLOSED_REPORT",
                severity="INFO",
                message=f"{summary.open_daily_reports} ta hisobot yopilmagan",
            ))

        # Packaging min-stock alerts
        pkg_wh_ids = await self._get_warehouse_ids(company_id, WarehouseType.PACKAGING)
        if pkg_wh_ids:
            from app.modules.packaging.service import PackagingService
            pkg_svc = PackagingService(self.session)
            for wh_id in pkg_wh_ids:
                pkg_alerts = await pkg_svc.get_min_stock_alerts(company_id, wh_id)
                for pa in pkg_alerts:
                    alerts.append(DashboardAlert(
                        alert_type="MIN_STOCK",
                        severity="WARNING",
                        message=f"{pa.display_name}: {pa.current_qty:.0f} {pa.unit_type} qoldi (min: {pa.min_qty:.0f})",
                    ))

        return alerts
