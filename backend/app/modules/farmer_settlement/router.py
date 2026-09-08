import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.farmer_settlement.schemas import (
    FarmerBalanceResponse,
    FarmerLedgerEntryResponse,
    FarmerPaymentCancel,
    FarmerPaymentCreate,
    FarmerPaymentResponse,
)
from app.modules.farmer_settlement.service import FarmerSettlementService
from app.shared.enums import FarmerPaymentStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/farmer-settlements", tags=["ginning-farmer-settlements"])


@router.get("/balances", response_model=list[FarmerBalanceResponse])
async def list_farmer_balances(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[FarmerBalanceResponse]:
    async with session.begin():
        svc = FarmerSettlementService(session)
        return await svc.list_farmer_balances(current_user.company_id)


@router.get("/farmers/{farmer_id}/statement", response_model=PaginatedResponse[FarmerLedgerEntryResponse])
async def get_farmer_statement(
    farmer_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> PaginatedResponse[FarmerLedgerEntryResponse]:
    async with session.begin():
        svc = FarmerSettlementService(session)
        return await svc.get_farmer_statement(current_user.company_id, farmer_id, page, page_size)


@router.get("/payments", response_model=PaginatedResponse[FarmerPaymentResponse])
async def list_payments(
    session: SessionDep,
    current_user: CurrentUserDep,
    farmer_id: uuid.UUID | None = Query(None),
    status: FarmerPaymentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[FarmerPaymentResponse]:
    async with session.begin():
        svc = FarmerSettlementService(session)
        return await svc.list(current_user.company_id, page, page_size, farmer_id, status)


@router.post("/payments", response_model=FarmerPaymentResponse, status_code=201)
async def create_payment(
    body: FarmerPaymentCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> FarmerPaymentResponse:
    async with session.begin():
        svc = FarmerSettlementService(session)
        payment = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(payment)


@router.post("/payments/{payment_id}/post", response_model=FarmerPaymentResponse)
async def post_payment(
    payment_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> FarmerPaymentResponse:
    async with session.begin():
        svc = FarmerSettlementService(session)
        payment = await svc.post(
            payment_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(payment)


@router.post("/payments/{payment_id}/cancel", response_model=FarmerPaymentResponse)
async def cancel_payment(
    payment_id: uuid.UUID,
    body: FarmerPaymentCancel,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> FarmerPaymentResponse:
    async with session.begin():
        svc = FarmerSettlementService(session)
        payment = await svc.cancel(
            payment_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(payment)
