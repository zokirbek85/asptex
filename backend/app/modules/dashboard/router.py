from fastapi import APIRouter

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.dashboard.schemas import (
    ChartDataPoint,
    DashboardAlert,
    DashboardSummary,
    SlowStockItem,
    StockByLot,
    UnclosedReportItem,
)
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DashboardSummary:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_summary(current_user.company_id)


@router.get("/finished-goods-chart")
async def fg_chart(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict[str, list[ChartDataPoint]]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_fg_chart(current_user.company_id)


@router.get("/stock-by-lot", response_model=list[StockByLot])
async def stock_by_lot(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[StockByLot]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_stock_by_lot(current_user.company_id)


@router.get("/slow-stock", response_model=list[SlowStockItem])
async def slow_stock(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[SlowStockItem]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_slow_stock(current_user.company_id)


@router.get("/recent-shipments")
async def recent_shipments(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[dict]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_recent_shipments(current_user.company_id)


@router.get("/alerts", response_model=list[DashboardAlert])
async def get_alerts(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[DashboardAlert]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_alerts(current_user.company_id)


@router.get("/unclosed-reports", response_model=list[UnclosedReportItem])
async def unclosed_reports(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[UnclosedReportItem]:
    async with session.begin():
        svc = DashboardService(session)
        return await svc.get_unclosed_reports(current_user.company_id)
