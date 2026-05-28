from datetime import date
import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.finished_goods.schemas import (
    FinishedGoodsStockItem,
    LotStockBreakdown,
    ProductionReportItem,
    ShipmentReportItem,
)
from app.modules.finished_goods.service import FinishedGoodsService
from app.shared.enums import LotStatus

router = APIRouter(prefix="/finished-goods", tags=["finished-goods"])


@router.get("/stock", response_model=list[FinishedGoodsStockItem])
async def get_stock(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    lot_id: uuid.UUID | None = Query(None),
    count_id: uuid.UUID | None = Query(None),
    owner_id: uuid.UUID | None = Query(None),
    lot_status: LotStatus | None = Query(None),
) -> list[FinishedGoodsStockItem]:
    async with session.begin():
        svc = FinishedGoodsService(session)
        return await svc.get_stock(
            current_user.company_id, warehouse_id, lot_id, count_id, owner_id, lot_status
        )


@router.get("/stock/{lot_id}/breakdown", response_model=LotStockBreakdown)
async def get_lot_breakdown(
    lot_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LotStockBreakdown:
    async with session.begin():
        svc = FinishedGoodsService(session)
        return await svc.get_lot_breakdown(current_user.company_id, warehouse_id, lot_id)


@router.get("/production-report", response_model=list[ProductionReportItem])
async def production_report(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[ProductionReportItem]:
    async with session.begin():
        svc = FinishedGoodsService(session)
        return await svc.get_production_report(
            current_user.company_id, warehouse_id, date_from, date_to
        )


@router.get("/shipment-report", response_model=list[ShipmentReportItem])
async def shipment_report(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[ShipmentReportItem]:
    async with session.begin():
        svc = FinishedGoodsService(session)
        return await svc.get_shipment_report(
            current_user.company_id, warehouse_id, date_from, date_to
        )
