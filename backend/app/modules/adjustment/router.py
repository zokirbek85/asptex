import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminDep, SessionDep
from app.modules.adjustment.schemas import (
    AdjustmentCreate,
    AdjustmentLineCreate,
    AdjustmentResponse,
)
from app.modules.adjustment.service import AdjustmentService
from app.shared.enums import AdjustmentStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/adjustments", tags=["adjustments"])


def _ctx(request: Request, cu):
    return cu.to_audit_context(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


@router.get("/", response_model=PaginatedResponse[AdjustmentResponse])
async def list_adjustments(
    session: SessionDep,
    current_user: AdminDep,
    warehouse_id: uuid.UUID | None = Query(None),
    status: AdjustmentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[AdjustmentResponse]:
    async with session.begin():
        svc = AdjustmentService(session)
        return await svc.list(current_user.company_id, warehouse_id, status, page, page_size)


@router.post("/", response_model=AdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    body: AdjustmentCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> AdjustmentResponse:
    async with session.begin():
        svc = AdjustmentService(session)
        return await svc.create(current_user.company_id, body, _ctx(request, current_user))


@router.get("/{adjustment_id}", response_model=AdjustmentResponse)
async def get_adjustment(
    adjustment_id: uuid.UUID,
    session: SessionDep,
    current_user: AdminDep,
) -> AdjustmentResponse:
    async with session.begin():
        svc = AdjustmentService(session)
        return await svc.get(adjustment_id)


@router.put("/{adjustment_id}/lines", response_model=AdjustmentResponse)
async def update_lines(
    adjustment_id: uuid.UUID,
    body: list[AdjustmentLineCreate],
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> AdjustmentResponse:
    async with session.begin():
        svc = AdjustmentService(session)
        return await svc.update_lines(adjustment_id, body, _ctx(request, current_user))


@router.post("/{adjustment_id}/post", response_model=AdjustmentResponse)
async def post_adjustment(
    adjustment_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> AdjustmentResponse:
    async with session.begin():
        svc = AdjustmentService(session)
        return await svc.post(adjustment_id, _ctx(request, current_user))
