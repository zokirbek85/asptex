import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminDep, AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.core.exceptions import PermissionDeniedError
from app.modules.counterparty.schemas import (
    ContactCreate,
    ContactResponse,
    CounterpartyCreate,
    CounterpartyMerge,
    CounterpartyResponse,
    CounterpartyUpdate,
)
from app.modules.counterparty.service import CounterpartyService
from app.shared.enums import CounterpartyType
from app.shared.schemas import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/counterparties", tags=["counterparties"])


@router.get("/", response_model=PaginatedResponse[CounterpartyResponse])
async def list_counterparties(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    active_only: bool = Query(False),
    counterparty_type: CounterpartyType | None = Query(None),
) -> PaginatedResponse[CounterpartyResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[CounterpartyResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = CounterpartyService(session)
        result = await svc.list(
            current_user.company_id, page, page_size, active_only, counterparty_type, search
        )
    return PaginatedResponse[CounterpartyResponse].build(
        [CounterpartyResponse.model_validate(c) for c in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=CounterpartyResponse, status_code=status.HTTP_201_CREATED)
async def create_counterparty(
    body: CounterpartyCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CounterpartyResponse:
    if current_user.company_id is None:
        raise PermissionDeniedError("No active company context")
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return CounterpartyResponse.model_validate(cp)


@router.get("/{counterparty_id}", response_model=CounterpartyResponse)
async def get_counterparty(
    counterparty_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CounterpartyResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.get(counterparty_id)
    return CounterpartyResponse.model_validate(cp)


@router.put("/{counterparty_id}", response_model=CounterpartyResponse)
async def update_counterparty(
    counterparty_id: uuid.UUID,
    body: CounterpartyUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> CounterpartyResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.update(
            counterparty_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return CounterpartyResponse.model_validate(cp)


@router.post("/{counterparty_id}/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def add_contact(
    counterparty_id: uuid.UUID,
    body: ContactCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ContactResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        contact = await svc.add_contact(
            counterparty_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
            ),
        )
    return ContactResponse.model_validate(contact)


@router.delete("/{counterparty_id}/contacts/{contact_id}", response_model=MessageResponse)
async def remove_contact(
    counterparty_id: uuid.UUID,
    contact_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> MessageResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        await svc.remove_contact(
            counterparty_id,
            contact_id,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
            ),
        )
    return MessageResponse(message="Contact removed")


@router.patch("/{counterparty_id}/activate", response_model=CounterpartyResponse)
async def activate_counterparty(
    counterparty_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> CounterpartyResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.activate(counterparty_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CounterpartyResponse.model_validate(cp)


@router.patch("/{counterparty_id}/deactivate", response_model=CounterpartyResponse)
async def deactivate_counterparty(
    counterparty_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> CounterpartyResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.deactivate(counterparty_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CounterpartyResponse.model_validate(cp)


@router.post("/{counterparty_id}/merge", response_model=CounterpartyResponse)
async def merge_counterparty(
    counterparty_id: uuid.UUID,
    body: CounterpartyMerge,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> CounterpartyResponse:
    async with session.begin():
        svc = CounterpartyService(session)
        cp = await svc.merge(
            target_id=counterparty_id,
            source_id=body.source_id,
            ctx=current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
            reason=body.reason,
        )
    return CounterpartyResponse.model_validate(cp)
