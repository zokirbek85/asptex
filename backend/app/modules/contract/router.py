import uuid

from fastapi import APIRouter, Query, Request, status

from app.core.dependencies import AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.core.exceptions import PermissionDeniedError
from app.modules.contract.schemas import ContractCreate, ContractResponse, ContractUpdate
from app.modules.contract.service import ContractService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/contracts", tags=["contracts"])


def _build_response(contract) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        company_id=contract.company_id,
        contract_number=contract.contract_number,
        contract_date=contract.contract_date,
        counterparty_id=contract.counterparty_id,
        counterparty_name=contract.counterparty.name if contract.counterparty else "",
        description=contract.description,
        is_active=contract.is_active,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.get("/", response_model=PaginatedResponse[ContractResponse])
async def list_contracts(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    active_only: bool = Query(False),
    counterparty_id: uuid.UUID | None = Query(None),
) -> PaginatedResponse[ContractResponse]:
    if current_user.company_id is None:
        return PaginatedResponse[ContractResponse].build([], 0, page, page_size)
    async with session.begin():
        svc = ContractService(session)
        result = await svc.list(
            current_user.company_id, page, page_size, active_only, counterparty_id, search
        )
    return PaginatedResponse[ContractResponse].build(
        [_build_response(c) for c in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ContractResponse:
    if current_user.company_id is None:
        raise PermissionDeniedError("No active company context")
    async with session.begin():
        svc = ContractService(session)
        contract = await svc.create(
            current_user.company_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return _build_response(contract)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ContractResponse:
    async with session.begin():
        svc = ContractService(session)
        contract = await svc.get(contract_id)
    return _build_response(contract)


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: uuid.UUID,
    body: ContractUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ContractResponse:
    async with session.begin():
        svc = ContractService(session)
        contract = await svc.update(
            contract_id,
            body,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return _build_response(contract)


@router.patch("/{contract_id}/activate", response_model=ContractResponse)
async def activate_contract(
    contract_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminOrDeputyDep,
) -> ContractResponse:
    async with session.begin():
        svc = ContractService(session)
        contract = await svc.activate(contract_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return _build_response(contract)


@router.patch("/{contract_id}/deactivate", response_model=ContractResponse)
async def deactivate_contract(
    contract_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminOrDeputyDep,
) -> ContractResponse:
    async with session.begin():
        svc = ContractService(session)
        contract = await svc.deactivate(contract_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return _build_response(contract)
