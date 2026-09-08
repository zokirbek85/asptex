import uuid
from datetime import date

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.ginning_costing.schemas import (
    CostAllocationRequest,
    GinningProductionCostCreate,
    GinningProductionCostResponse,
    ProductionCostSummaryResponse,
    ProductProfitabilityResponse,
)
from app.modules.ginning_costing.service import GinningCostingService
from app.shared.enums import CostAllocationMethod

router = APIRouter(prefix="/ginning/costing", tags=["ginning-costing"])


@router.post("/production-orders/{order_id}/costs", response_model=GinningProductionCostResponse, status_code=201)
async def add_cost(
    order_id: uuid.UUID,
    body: GinningProductionCostCreate,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> GinningProductionCostResponse:
    async with session.begin():
        svc = GinningCostingService(session)
        cost = await svc.add_cost(current_user.company_id, order_id, body, current_user.user_id)
        return GinningProductionCostResponse(
            id=cost.id, production_order_id=cost.production_order_id, cost_type=cost.cost_type,
            amount=cost.amount, currency=cost.currency, notes=cost.notes, created_at=cost.created_at,
        )


@router.get("/production-orders/{order_id}/summary", response_model=ProductionCostSummaryResponse)
async def get_cost_summary(
    order_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    method: CostAllocationMethod = Query(CostAllocationMethod.QUANTITY),
) -> ProductionCostSummaryResponse:
    async with session.begin():
        svc = GinningCostingService(session)
        return await svc.get_cost_summary(
            current_user.company_id, order_id, CostAllocationRequest(method=method)
        )


@router.post("/production-orders/{order_id}/summary", response_model=ProductionCostSummaryResponse)
async def get_cost_summary_with_manual_pct(
    order_id: uuid.UUID,
    body: CostAllocationRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProductionCostSummaryResponse:
    async with session.begin():
        svc = GinningCostingService(session)
        return await svc.get_cost_summary(current_user.company_id, order_id, body)


@router.get("/profitability", response_model=list[ProductProfitabilityResponse])
async def get_profitability(
    session: SessionDep,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[ProductProfitabilityResponse]:
    async with session.begin():
        svc = GinningCostingService(session)
        return await svc.get_product_profitability(current_user.company_id, date_from, date_to)
