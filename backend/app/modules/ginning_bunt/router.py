import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.ginning_bunt.schemas import (
    GinningBuntClose,
    GinningBuntCreate,
    GinningBuntDetailResponse,
    GinningBuntResponse,
)
from app.modules.ginning_bunt.service import GinningBuntService
from app.shared.enums import BuntStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/bunts", tags=["ginning-bunts"])


@router.get("/", response_model=PaginatedResponse[GinningBuntResponse])
async def list_bunts(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID | None = Query(None),
    status: BuntStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[GinningBuntResponse]:
    async with session.begin():
        svc = GinningBuntService(session)
        return await svc.list(current_user.company_id, page, page_size, warehouse_id, status)


@router.post("/", response_model=GinningBuntResponse, status_code=201)
async def create_bunt(
    body: GinningBuntCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningBuntResponse:
    async with session.begin():
        svc = GinningBuntService(session)
        bunt = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(bunt)


@router.get("/{bunt_id}", response_model=GinningBuntDetailResponse)
async def get_bunt(
    bunt_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningBuntDetailResponse:
    async with session.begin():
        svc = GinningBuntService(session)
        return await svc.get_detail(bunt_id, current_user.company_id)


@router.patch("/{bunt_id}/close", response_model=GinningBuntResponse)
async def close_bunt(
    bunt_id: uuid.UUID,
    body: GinningBuntClose,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> GinningBuntResponse:
    async with session.begin():
        svc = GinningBuntService(session)
        bunt = await svc.close(
            bunt_id,
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(bunt)


@router.patch("/{bunt_id}/reopen", response_model=GinningBuntResponse)
async def reopen_bunt(
    bunt_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> GinningBuntResponse:
    async with session.begin():
        svc = GinningBuntService(session)
        bunt = await svc.reopen(
            bunt_id,
            current_user.company_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
        return svc.build_response(bunt)
