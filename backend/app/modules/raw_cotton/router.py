from datetime import date
import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.raw_cotton.schemas import (
    CottonBalanceSummary,
    ProductionIssueItem,
    RawCottonStockItem,
)
from app.modules.raw_cotton.service import RawCottonService

router = APIRouter(prefix="/raw-cotton", tags=["raw-cotton"])


@router.get("/stock", response_model=list[RawCottonStockItem])
async def get_stock(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[RawCottonStockItem]:
    async with session.begin():
        svc = RawCottonService(session)
        return await svc.get_stock(current_user.company_id, warehouse_id)


@router.get("/production-issue-report", response_model=list[ProductionIssueItem])
async def production_issue_report(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[ProductionIssueItem]:
    async with session.begin():
        svc = RawCottonService(session)
        return await svc.get_production_issue_report(
            current_user.company_id, warehouse_id, date_from, date_to
        )


@router.get("/balance-summary", response_model=CottonBalanceSummary)
async def balance_summary(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CottonBalanceSummary:
    async with session.begin():
        svc = RawCottonService(session)
        return await svc.get_balance_summary(current_user.company_id, warehouse_id)
