import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.intercompany_transfer.schemas import (
    IntercompanyTransferCancel,
    IntercompanyTransferCreate,
    IntercompanyTransferResponse,
)
from app.modules.intercompany_transfer.service import IntercompanyTransferService
from app.shared.enums import IntercompanyTransferStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/intercompany-transfers", tags=["ginning-intercompany-transfers"])


@router.get("/", response_model=PaginatedResponse[IntercompanyTransferResponse])
async def list_transfers(
    session: SessionDep,
    current_user: CurrentUserDep,
    status: IntercompanyTransferStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[IntercompanyTransferResponse]:
    async with session.begin():
        svc = IntercompanyTransferService(session)
        return await svc.list(current_user.company_id, page, page_size, status)


@router.post("/", response_model=IntercompanyTransferResponse, status_code=201)
async def create_transfer(
    body: IntercompanyTransferCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> IntercompanyTransferResponse:
    async with session.begin():
        svc = IntercompanyTransferService(session)
        transfer = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(transfer)


@router.get("/{transfer_id}", response_model=IntercompanyTransferResponse)
async def get_transfer(
    transfer_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> IntercompanyTransferResponse:
    async with session.begin():
        svc = IntercompanyTransferService(session)
        transfer = await svc.get(transfer_id, current_user.company_id)
        return await svc.build_response(transfer)


@router.post("/{transfer_id}/confirm", response_model=IntercompanyTransferResponse)
async def confirm_transfer(
    transfer_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> IntercompanyTransferResponse:
    async with session.begin():
        svc = IntercompanyTransferService(session)
        transfer = await svc.confirm(
            transfer_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(transfer)


@router.post("/{transfer_id}/cancel", response_model=IntercompanyTransferResponse)
async def cancel_transfer(
    transfer_id: uuid.UUID,
    body: IntercompanyTransferCancel,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> IntercompanyTransferResponse:
    async with session.begin():
        svc = IntercompanyTransferService(session)
        transfer = await svc.cancel(
            transfer_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return await svc.build_response(transfer)
