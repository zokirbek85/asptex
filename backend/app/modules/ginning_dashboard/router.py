from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.ginning_dashboard.schemas import (
    ChartDataPoint,
    GinningDashboardSummary,
    GinningReceivingTrendPoint,
)
from app.modules.ginning_dashboard.service import GinningDashboardService

router = APIRouter(prefix="/ginning/dashboard", tags=["ginning-dashboard"])


@router.get("/summary", response_model=GinningDashboardSummary)
async def get_summary(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningDashboardSummary:
    async with session.begin():
        svc = GinningDashboardService(session)
        return await svc.get_summary(current_user.company_id)


@router.get("/receiving-trend", response_model=list[GinningReceivingTrendPoint])
async def get_receiving_trend(
    session: SessionDep,
    current_user: CurrentUserDep,
    days: int = Query(30, ge=1, le=365),
) -> list[GinningReceivingTrendPoint]:
    async with session.begin():
        svc = GinningDashboardService(session)
        return await svc.get_receiving_trend(current_user.company_id, days)


@router.get("/output-distribution", response_model=list[ChartDataPoint])
async def get_output_distribution(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[ChartDataPoint]:
    async with session.begin():
        svc = GinningDashboardService(session)
        return await svc.get_output_distribution(current_user.company_id)
