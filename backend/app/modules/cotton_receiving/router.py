import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.cotton_receiving.schemas import (
    CottonPriceListCreate,
    CottonPriceListResponse,
    CottonReceivingCancel,
    CottonReceivingCreate,
    CottonReceivingResponse,
    CottonReceivingUpdate,
)
from app.modules.cotton_receiving.service import CottonReceivingService
from app.shared.enums import CottonReceivingStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/cotton-receiving", tags=["ginning-cotton-receiving"])


@router.get("/", response_model=PaginatedResponse[CottonReceivingResponse])
async def list_receivings(
    session: SessionDep,
    current_user: CurrentUserDep,
    bunt_id: uuid.UUID | None = Query(None),
    farmer_id: uuid.UUID | None = Query(None),
    status: CottonReceivingStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[CottonReceivingResponse]:
    async with session.begin():
        svc = CottonReceivingService(session)
        return await svc.list(current_user.company_id, page, page_size, bunt_id, farmer_id, status)


@router.post("/", response_model=CottonReceivingResponse, status_code=201)
async def create_receiving(
    body: CottonReceivingCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CottonReceivingResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        r = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        bunt_lot_number = await svc.bunt_lot_number(r.bunt_id, current_user.company_id)
        return svc.build_response(r, bunt_lot_number)


@router.get("/{receiving_id}", response_model=CottonReceivingResponse)
async def get_receiving(
    receiving_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CottonReceivingResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        r = await svc.get(receiving_id, current_user.company_id)
        bunt_lot_number = await svc.bunt_lot_number(r.bunt_id, current_user.company_id)
        return svc.build_response(r, bunt_lot_number)


@router.put("/{receiving_id}", response_model=CottonReceivingResponse)
async def update_receiving(
    receiving_id: uuid.UUID,
    body: CottonReceivingUpdate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CottonReceivingResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        r = await svc.update(
            receiving_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        bunt_lot_number = await svc.bunt_lot_number(r.bunt_id, current_user.company_id)
        return svc.build_response(r, bunt_lot_number)


@router.post("/{receiving_id}/post", response_model=CottonReceivingResponse)
async def post_receiving(
    receiving_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CottonReceivingResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        r = await svc.post(
            receiving_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        bunt_lot_number = await svc.bunt_lot_number(r.bunt_id, current_user.company_id)
        return svc.build_response(r, bunt_lot_number)


@router.post("/{receiving_id}/cancel", response_model=CottonReceivingResponse)
async def cancel_receiving(
    receiving_id: uuid.UUID,
    body: CottonReceivingCancel,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CottonReceivingResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        r = await svc.cancel(
            receiving_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        bunt_lot_number = await svc.bunt_lot_number(r.bunt_id, current_user.company_id)
        return svc.build_response(r, bunt_lot_number)


@router.get("/price-list/", response_model=list[CottonPriceListResponse])
async def list_price_rules(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[CottonPriceListResponse]:
    async with session.begin():
        svc = CottonReceivingService(session)
        return await svc.list_price_rules(current_user.company_id)


@router.post("/price-list/", response_model=CottonPriceListResponse, status_code=201)
async def create_price_rule(
    body: CottonPriceListCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CottonPriceListResponse:
    async with session.begin():
        svc = CottonReceivingService(session)
        return await svc.create_price_rule(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
