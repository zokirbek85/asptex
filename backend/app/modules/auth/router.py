from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import CurrentUser, CurrentUserDep, get_current_user
from app.modules.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    SwitchCompanyRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService
from app.shared.schemas import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    async with session.begin():
        service = AuthService(session)
        return await service.login(
            username=body.username,
            password=body.password,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )


@router.post("/switch-company", response_model=AccessTokenResponse)
async def switch_company(
    body: SwitchCompanyRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccessTokenResponse:
    async with session.begin():
        service = AuthService(session)
        return await service.switch_company(
            user_id=current_user.user_id,
            company_id=body.company_id,
        )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccessTokenResponse:
    async with session.begin():
        service = AuthService(session)
        return await service.refresh(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    async with session.begin():
        service = AuthService(session)
        await service.logout(body.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeResponse:
    async with session.begin():
        service = AuthService(session)
        user = await service.get_me(current_user.user_id)
    return MeResponse(
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superadmin=user.is_superadmin,
            preferred_language=user.preferred_language,
            created_at=user.created_at,
        ),
        company_id=current_user.company_id,
        role=current_user.role,
        warehouse_id=current_user.warehouse_id,
    )
