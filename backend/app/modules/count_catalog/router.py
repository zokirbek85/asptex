import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.core.exceptions import PermissionDeniedError
from app.modules.count_catalog.schemas import CountCreate, CountResponse, CountUpdate
from app.modules.count_catalog.service import CountCatalogService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/counts", tags=["count-catalog"])


@router.get("/", response_model=PaginatedResponse[CountResponse])
async def list_counts(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    search: str | None = Query(None),
    active_only: bool = Query(False),
) -> PaginatedResponse[CountResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[CountResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = CountCatalogService(session)
        result = await svc.list(current_user.company_id, page, page_size, active_only, search)
    return PaginatedResponse[CountResponse].build(
        [CountResponse.model_validate(c) for c in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=CountResponse, status_code=status.HTTP_201_CREATED)
async def create_count(
    body: CountCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CountResponse:
    if current_user.company_id is None:
        raise PermissionDeniedError("No active company context")
    async with session.begin():
        svc = CountCatalogService(session)
        count = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return CountResponse.model_validate(count)


@router.get("/{count_id}", response_model=CountResponse)
async def get_count(
    count_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CountResponse:
    async with session.begin():
        svc = CountCatalogService(session)
        count = await svc.get(count_id)
    return CountResponse.model_validate(count)


@router.put("/{count_id}", response_model=CountResponse)
async def update_count(
    count_id: uuid.UUID,
    body: CountUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CountResponse:
    async with session.begin():
        svc = CountCatalogService(session)
        count = await svc.update(
            count_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return CountResponse.model_validate(count)


@router.patch("/{count_id}/activate", response_model=CountResponse)
async def activate_count(
    count_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminOrDeputyDep,
) -> CountResponse:
    async with session.begin():
        svc = CountCatalogService(session)
        count = await svc.activate(count_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CountResponse.model_validate(count)


@router.patch("/{count_id}/deactivate", response_model=CountResponse)
async def deactivate_count(
    count_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminOrDeputyDep,
) -> CountResponse:
    async with session.begin():
        svc = CountCatalogService(session)
        count = await svc.deactivate(count_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CountResponse.model_validate(count)
