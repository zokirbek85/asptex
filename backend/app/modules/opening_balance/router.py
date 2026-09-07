import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminDep, CurrentUserDep, SessionDep
from app.modules.opening_balance.schemas import (
    OpeningBalanceCreate,
    OpeningBalanceLineCreate,
    OpeningBalanceResponse,
)
from app.modules.opening_balance.service import OpeningBalanceService
from app.shared.enums import AdjustmentStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/opening-balances", tags=["opening-balances"])


@router.get("/", response_model=PaginatedResponse[OpeningBalanceResponse])
async def list_opening_balances(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID | None = Query(None),
    status: AdjustmentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[OpeningBalanceResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[OpeningBalanceResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = OpeningBalanceService(session)
        return await svc.list(current_user.company_id, warehouse_id, status, page, page_size)


@router.post("/", response_model=OpeningBalanceResponse, status_code=status.HTTP_201_CREATED)
async def create_opening_balance(
    body: OpeningBalanceCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> OpeningBalanceResponse:
    async with session.begin():
        svc = OpeningBalanceService(session)
        return await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )


@router.get("/{entry_id}", response_model=OpeningBalanceResponse)
async def get_opening_balance(
    entry_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> OpeningBalanceResponse:
    async with session.begin():
        svc = OpeningBalanceService(session)
        return await svc.get(entry_id, current_user.company_id)


@router.put("/{entry_id}/lines", response_model=OpeningBalanceResponse)
async def update_lines(
    entry_id: uuid.UUID,
    lines: list[OpeningBalanceLineCreate],
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> OpeningBalanceResponse:
    async with session.begin():
        svc = OpeningBalanceService(session)
        return await svc.update_lines(
            entry_id,
            current_user.company_id,
            lines,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )


@router.post("/{entry_id}/post", response_model=OpeningBalanceResponse)
async def post_opening_balance(
    entry_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> OpeningBalanceResponse:
    async with session.begin():
        svc = OpeningBalanceService(session)
        return await svc.post(
            entry_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opening_balance(
    entry_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> None:
    async with session.begin():
        svc = OpeningBalanceService(session)
        await svc.delete(
            entry_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
