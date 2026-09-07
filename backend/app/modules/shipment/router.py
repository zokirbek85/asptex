from datetime import date
import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.shipment.schemas import (
    ShipmentCreate,
    ShipmentLineCancelRequest,
    ShipmentResponse,
)
from app.modules.shipment.service import ShipmentService
from app.shared.enums import ShipmentStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/shipments", tags=["shipments"])


def _ctx(request: Request, cu):
    return cu.to_audit_context(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


@router.get("/by-number/{number}", response_model=ShipmentResponse)
async def get_by_number(
    number: str,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ShipmentResponse:
    async with session.begin():
        svc = ShipmentService(session)
        from app.core.exceptions import NotFoundError
        shipment = await svc.repo.get_by_number(current_user.company_id, number)
        if shipment is None:
            raise NotFoundError("Shipment", number)
        return await svc.build_response(shipment)


@router.get("/", response_model=PaginatedResponse[ShipmentResponse])
async def list_shipments(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID | None = Query(None),
    buyer_id: uuid.UUID | None = Query(None),
    lot_id: uuid.UUID | None = Query(None),
    status: ShipmentStatus | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[ShipmentResponse]:
    async with session.begin():
        svc = ShipmentService(session)
        result = await svc.list(
            current_user.company_id, warehouse_id, buyer_id, status, lot_id,
            date_from, date_to, page, page_size,
        )
        responses = [await svc.build_response(s) for s in result.items]
    return PaginatedResponse[ShipmentResponse].build(
        responses, result.total, result.page, result.page_size
    )


@router.post("/", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    body: ShipmentCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ShipmentResponse:
    async with session.begin():
        svc = ShipmentService(session)
        shipment = await svc.create(current_user.company_id, body, _ctx(request, current_user))
        return await svc.build_response(shipment)


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ShipmentResponse:
    async with session.begin():
        svc = ShipmentService(session)
        shipment = await svc.get(shipment_id, current_user.company_id)
        return await svc.build_response(shipment)


@router.post("/{shipment_id}/lines/{line_id}/cancel", response_model=ShipmentResponse)
async def cancel_line(
    shipment_id: uuid.UUID,
    line_id: uuid.UUID,
    body: ShipmentLineCancelRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ShipmentResponse:
    async with session.begin():
        svc = ShipmentService(session)
        shipment = await svc.cancel_line(
            shipment_id, current_user.company_id, line_id, body, _ctx(request, current_user)
        )
        return await svc.build_response(shipment)
