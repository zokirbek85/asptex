import uuid

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select

from app.core.dependencies import AdminDep, AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.core.exceptions import PermissionDeniedError
from app.modules.lot.schemas import (
    LotClose,
    LotCreate,
    LotReopen,
    LotResponse,
    LotUpdate,
    StockSummaryItem,
)
from app.modules.lot.service import LotService
from app.modules.tolling.models import TollingLot as TollingLotModel
from app.shared.enums import LotStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/lots", tags=["lots"])


def _build_response(lot, stock_summary: list[dict] | None = None, tolling_lot_id: uuid.UUID | None = None) -> LotResponse:
    return LotResponse(
        id=lot.id,
        company_id=lot.company_id,
        lot_number=lot.lot_number,
        year=lot.year,
        sequence_number=lot.sequence_number,
        status=lot.status,
        opened_at=lot.opened_at,
        closed_at=lot.closed_at,
        closed_by=lot.closed_by,
        close_reason=lot.close_reason,
        auto_closed=lot.auto_closed,
        notes=lot.notes,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
        stock_summary=[StockSummaryItem(**s) for s in (stock_summary or [])],
        tolling_lot_id=tolling_lot_id,
    )


async def _get_tolling_lot_map(session, lot_ids: list[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
    if not lot_ids:
        return {}
    result = await session.execute(
        select(TollingLotModel.lot_id, TollingLotModel.id).where(
            TollingLotModel.lot_id.in_(lot_ids)
        )
    )
    return {r.lot_id: r.id for r in result}


@router.get("/", response_model=PaginatedResponse[LotResponse])
async def list_lots(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    status: LotStatus | None = Query(None),
) -> PaginatedResponse[LotResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[LotResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = LotService(session)
        result = await svc.list(current_user.company_id, page, page_size, status, search)
        lot_ids = [lot.id for lot in result.items]
        tolling_map = await _get_tolling_lot_map(session, lot_ids)
    return PaginatedResponse[LotResponse].build(
        [_build_response(lot, tolling_lot_id=tolling_map.get(lot.id)) for lot in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=LotResponse, status_code=status.HTTP_201_CREATED)
async def create_lot(
    body: LotCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> LotResponse:
    if current_user.company_id is None:
        raise PermissionDeniedError("No active company context")
    async with session.begin():
        svc = LotService(session)
        lot = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return _build_response(lot)


@router.get("/{lot_id}", response_model=LotResponse)
async def get_lot(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    include_stock: bool = Query(False),
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.get(lot_id)
        summary = await svc.get_stock_summary(lot_id) if include_stock else None
        tolling_map = await _get_tolling_lot_map(session, [lot_id])
    return _build_response(lot, summary, tolling_lot_id=tolling_map.get(lot_id))


@router.put("/{lot_id}", response_model=LotResponse)
async def update_lot(
    lot_id: uuid.UUID,
    body: LotUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.update(lot_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return _build_response(lot)


@router.get("/{lot_id}/stock", response_model=list[StockSummaryItem])
async def get_lot_stock(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[StockSummaryItem]:
    async with session.begin():
        svc = LotService(session)
        summary = await svc.get_stock_summary(lot_id)
    return [StockSummaryItem(**s) for s in summary]


@router.patch("/{lot_id}/close", response_model=LotResponse)
async def close_lot(
    lot_id: uuid.UUID,
    body: LotClose,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.close(lot_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return _build_response(lot)


@router.patch("/{lot_id}/reopen", response_model=LotResponse)
async def reopen_lot(
    lot_id: uuid.UUID,
    body: LotReopen,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.reopen(lot_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return _build_response(lot)


@router.patch("/{lot_id}/block", response_model=LotResponse)
async def block_lot(
    lot_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.block(lot_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return _build_response(lot)


@router.patch("/{lot_id}/unblock", response_model=LotResponse)
async def unblock_lot(
    lot_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> LotResponse:
    async with session.begin():
        svc = LotService(session)
        lot = await svc.unblock(lot_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return _build_response(lot)
