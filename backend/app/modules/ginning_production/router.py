import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.ginning_production.schemas import (
    GinningProductionCancel,
    GinningProductionOrderCreate,
    GinningProductionOrderResponse,
    GinningProductionOrderUpdate,
)
from app.modules.ginning_production.service import GinningProductionService
from app.shared.enums import GinningProductionStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/production", tags=["ginning-production"])


@router.get("/", response_model=PaginatedResponse[GinningProductionOrderResponse])
async def list_orders(
    session: SessionDep,
    current_user: CurrentUserDep,
    status: GinningProductionStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[GinningProductionOrderResponse]:
    async with session.begin():
        svc = GinningProductionService(session)
        return await svc.list(current_user.company_id, page, page_size, status)


@router.post("/", response_model=GinningProductionOrderResponse, status_code=201)
async def create_order(
    body: GinningProductionOrderCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningProductionOrderResponse:
    async with session.begin():
        svc = GinningProductionService(session)
        order = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(order)


@router.get("/{order_id}", response_model=GinningProductionOrderResponse)
async def get_order(
    order_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningProductionOrderResponse:
    async with session.begin():
        svc = GinningProductionService(session)
        order = await svc.get(order_id, current_user.company_id)
        return await svc.build_response(order)


@router.put("/{order_id}", response_model=GinningProductionOrderResponse)
async def update_order(
    order_id: uuid.UUID,
    body: GinningProductionOrderUpdate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningProductionOrderResponse:
    async with session.begin():
        svc = GinningProductionService(session)
        order = await svc.update(
            order_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(order)


@router.post("/{order_id}/complete", response_model=GinningProductionOrderResponse)
async def complete_order(
    order_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningProductionOrderResponse:
    async with session.begin():
        svc = GinningProductionService(session)
        order = await svc.complete(
            order_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(order)


@router.post("/{order_id}/cancel", response_model=GinningProductionOrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    body: GinningProductionCancel,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> GinningProductionOrderResponse:
    async with session.begin():
        svc = GinningProductionService(session)
        order = await svc.cancel(
            order_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(order)
