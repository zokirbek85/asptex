import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminDep, CurrentUserDep, SessionDep
from app.modules.warehouse.schemas import WarehouseCreate, WarehouseResponse, WarehouseUpdate
from app.modules.warehouse.service import WarehouseService
from app.shared.enums import WarehouseType
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("/", response_model=PaginatedResponse[WarehouseResponse])
async def list_warehouses(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    active_only: bool = Query(False),
    warehouse_type: WarehouseType | None = Query(None),
) -> PaginatedResponse[WarehouseResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[WarehouseResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = WarehouseService(session)
        result = await svc.list(
            current_user.company_id, page, page_size, active_only, warehouse_type
        )
    return PaginatedResponse[WarehouseResponse].build(
        [WarehouseResponse.model_validate(w) for w in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> WarehouseResponse:
    if current_user.company_id is None:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError("No active company context")
    async with session.begin():
        svc = WarehouseService(session)
        warehouse = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return WarehouseResponse.model_validate(warehouse)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WarehouseResponse:
    async with session.begin():
        svc = WarehouseService(session)
        warehouse = await svc.get(warehouse_id)
    return WarehouseResponse.model_validate(warehouse)


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    body: WarehouseUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> WarehouseResponse:
    async with session.begin():
        svc = WarehouseService(session)
        warehouse = await svc.update(
            warehouse_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return WarehouseResponse.model_validate(warehouse)


@router.patch("/{warehouse_id}/activate", response_model=WarehouseResponse)
async def activate_warehouse(
    warehouse_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> WarehouseResponse:
    async with session.begin():
        svc = WarehouseService(session)
        warehouse = await svc.activate(warehouse_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return WarehouseResponse.model_validate(warehouse)


@router.patch("/{warehouse_id}/deactivate", response_model=WarehouseResponse)
async def deactivate_warehouse(
    warehouse_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> WarehouseResponse:
    async with session.begin():
        svc = WarehouseService(session)
        warehouse = await svc.deactivate(warehouse_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return WarehouseResponse.model_validate(warehouse)
