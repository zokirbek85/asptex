import uuid

from fastapi import APIRouter, Query, Request

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.ginning_bale.schemas import GinningBaleCreate, GinningBaleCreateResult, GinningBaleResponse
from app.modules.ginning_bale.service import GinningBaleService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/ginning/bales", tags=["ginning-bales"])


@router.get("/", response_model=PaginatedResponse[GinningBaleResponse])
async def list_bales(
    session: SessionDep,
    current_user: CurrentUserDep,
    production_order_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[GinningBaleResponse]:
    async with session.begin():
        svc = GinningBaleService(session)
        return await svc.list(current_user.company_id, page, page_size, production_order_id)


@router.post("/", response_model=GinningBaleCreateResult, status_code=201)
async def create_bale(
    body: GinningBaleCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningBaleCreateResult:
    async with session.begin():
        svc = GinningBaleService(session)
        return await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )


@router.get("/{bale_id}", response_model=GinningBaleResponse)
async def get_bale(
    bale_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GinningBaleResponse:
    async with session.begin():
        svc = GinningBaleService(session)
        bale = await svc.get(bale_id, current_user.company_id)
        order = await svc.order_repo.get_by_id(bale.production_order_id)
        return svc.build_response(bale, order.production_number if order else "")
