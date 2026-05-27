import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import AdminDep, CurrentUserDep, SessionDep
from app.modules.company.schemas import CompanyCreate, CompanyResponse, CompanyUpdate
from app.modules.company.service import CompanyService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=PaginatedResponse[CompanyResponse])
async def list_companies(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    active_only: bool = Query(False),
) -> PaginatedResponse[CompanyResponse]:
    async with session.begin():
        svc = CompanyService(session)
        result = await svc.list(page, page_size, active_only, search)
    return PaginatedResponse[CompanyResponse].build(
        [CompanyResponse.model_validate(c) for c in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> CompanyResponse:
    async with session.begin():
        svc = CompanyService(session)
        company = await svc.create(body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
    return CompanyResponse.model_validate(company)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CompanyResponse:
    async with session.begin():
        svc = CompanyService(session)
        company = await svc.get(company_id)
    return CompanyResponse.model_validate(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> CompanyResponse:
    async with session.begin():
        svc = CompanyService(session)
        company = await svc.update(company_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
    return CompanyResponse.model_validate(company)


@router.patch("/{company_id}/activate", response_model=CompanyResponse)
async def activate_company(
    company_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> CompanyResponse:
    async with session.begin():
        svc = CompanyService(session)
        company = await svc.activate(company_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CompanyResponse.model_validate(company)


@router.patch("/{company_id}/deactivate", response_model=CompanyResponse)
async def deactivate_company(
    company_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> CompanyResponse:
    async with session.begin():
        svc = CompanyService(session)
        company = await svc.deactivate(company_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return CompanyResponse.model_validate(company)
