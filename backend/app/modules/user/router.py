import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import AdminDep, CurrentUserDep, SessionDep
from app.modules.user.schemas import (
    UserCreate,
    UserPasswordChange,
    UserResponse,
    UserRoleAssign,
    UserRoleResponse,
    UserRoleUpdate,
    UserUpdate,
)
from app.modules.user.service import UserService
from app.shared.schemas import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])


def _build_role_response(role) -> UserRoleResponse:
    return UserRoleResponse(
        id=role.id,
        user_id=role.user_id,
        company_id=role.company_id,
        company_name=role.company.name if role.company else "",
        role=role.role,
        warehouse_id=role.warehouse_id,
        warehouse_name=role.warehouse.name if role.warehouse else None,
        is_active=role.is_active,
        created_at=role.created_at,
    )


def _build_user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
        preferred_language=user.preferred_language,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=[_build_role_response(r) for r in getattr(user, "company_roles", [])],
    )


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    session: SessionDep,
    current_user: AdminDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    active_only: bool = Query(False),
) -> PaginatedResponse[UserResponse]:
    async with session.begin():
        svc = UserService(session)
        result = await svc.list(page, page_size, active_only, search)
    return PaginatedResponse[UserResponse].build(
        [_build_user_response(u) for u in result.items],
        result.total, result.page, result.page_size,
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> UserResponse:
    async with session.begin():
        svc = UserService(session)
        user = await svc.create(body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
    return _build_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: AdminDep,
) -> UserResponse:
    async with session.begin():
        svc = UserService(session)
        user = await svc.get(user_id)
    return _build_user_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> UserResponse:
    async with session.begin():
        svc = UserService(session)
        user = await svc.update(user_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
    return _build_user_response(user)


@router.patch("/{user_id}/password", response_model=MessageResponse)
async def change_password(
    user_id: uuid.UUID,
    body: UserPasswordChange,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> MessageResponse:
    async with session.begin():
        svc = UserService(session)
        await svc.change_password(
            user_id,
            body.new_password,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
    return MessageResponse(message="Password updated successfully")


@router.patch("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> UserResponse:
    async with session.begin():
        svc = UserService(session)
        user = await svc.activate(user_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return _build_user_response(user)


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID, request: Request, session: SessionDep, current_user: AdminDep,
) -> UserResponse:
    async with session.begin():
        svc = UserService(session)
        user = await svc.deactivate(user_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None))
    return _build_user_response(user)


@router.post("/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role(
    user_id: uuid.UUID,
    body: UserRoleAssign,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> UserRoleResponse:
    async with session.begin():
        svc = UserService(session)
        role = await svc.assign_role(user_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
        # Re-fetch with relationships for response
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.modules.user.models import UserCompanyRole
        result = await session.execute(
            select(UserCompanyRole)
            .where(UserCompanyRole.id == role.id)
            .options(
                selectinload(UserCompanyRole.company),
                selectinload(UserCompanyRole.warehouse),
            )
        )
        role = result.scalar_one()
    return _build_role_response(role)


@router.put("/{user_id}/roles/{company_id}", response_model=UserRoleResponse)
async def update_role(
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    body: UserRoleUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> UserRoleResponse:
    async with session.begin():
        svc = UserService(session)
        role = await svc.update_role(user_id, company_id, body, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.modules.user.models import UserCompanyRole
        result = await session.execute(
            select(UserCompanyRole)
            .where(UserCompanyRole.id == role.id)
            .options(
                selectinload(UserCompanyRole.company),
                selectinload(UserCompanyRole.warehouse),
            )
        )
        role = result.scalar_one()
    return _build_role_response(role)


@router.delete("/{user_id}/roles/{company_id}", response_model=MessageResponse)
async def remove_role(
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> MessageResponse:
    async with session.begin():
        svc = UserService(session)
        await svc.remove_role(user_id, company_id, current_user.to_audit_context(
            ip_address=request.client.host if request.client else None,
        ))
    return MessageResponse(message="Role removed successfully")
