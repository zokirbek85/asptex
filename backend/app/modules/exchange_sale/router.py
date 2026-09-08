import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.exchange_sale.schemas import (
    ExchangeSaleCreate,
    ExchangeSaleLineCancelRequest,
    ExchangeSaleResponse,
)
from app.modules.exchange_sale.service import ExchangeSaleService
from app.shared.enums import ExchangeSaleStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/exchange-sales", tags=["ginning-exchange-sales"])


@router.get("/", response_model=PaginatedResponse[ExchangeSaleResponse])
async def list_sales(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    status: ExchangeSaleStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[ExchangeSaleResponse]:
    async with session.begin():
        svc = ExchangeSaleService(session)
        return await svc.list(current_user.company_id, page, page_size, warehouse_id, customer_id, status)


@router.post("/", response_model=ExchangeSaleResponse, status_code=201)
async def create_sale(
    body: ExchangeSaleCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ExchangeSaleResponse:
    async with session.begin():
        svc = ExchangeSaleService(session)
        sale = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(sale)


@router.get("/{sale_id}", response_model=ExchangeSaleResponse)
async def get_sale(
    sale_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ExchangeSaleResponse:
    async with session.begin():
        svc = ExchangeSaleService(session)
        sale = await svc.get(sale_id, current_user.company_id)
        return await svc.build_response(sale)


@router.post("/{sale_id}/lines/{line_id}/cancel", response_model=ExchangeSaleResponse)
async def cancel_line(
    sale_id: uuid.UUID,
    line_id: uuid.UUID,
    body: ExchangeSaleLineCancelRequest,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ExchangeSaleResponse:
    async with session.begin():
        svc = ExchangeSaleService(session)
        sale = await svc.cancel_line(
            sale_id, current_user.company_id, line_id, body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(sale)
