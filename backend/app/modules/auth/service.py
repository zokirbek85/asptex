import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.repository import RefreshTokenRepository, UserRepository
from app.modules.auth.schemas import (
    AccessTokenResponse,
    CompanyBrief,
    TokenResponse,
    UserResponse,
)
from app.modules.user.models import UserCompanyRole
from app.shared.enums import UserRole


def _build_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
        preferred_language=user.preferred_language,
        created_at=user.created_at,
    )


def _build_company_list(user: User) -> list[CompanyBrief]:
    return [
        CompanyBrief(
            id=role.company_id,
            name=role.company.name,
            short_name=role.company.short_name,
            role=role.role,
            company_type=role.company.company_type,
        )
        for role in user.company_roles
        if role.is_active and role.company.is_active
    ]


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._user_repo = UserRepository(session)
        self._token_repo = RefreshTokenRepository(session)

    async def login(
        self,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        user = await self._user_repo.get_by_username(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid username or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        raw_refresh = create_refresh_token()
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(refresh_token)
        await self.session.flush()

        # Initial token has no company context — user picks company next
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            user=_build_user_response(user),
            companies=_build_company_list(user),
        )

    async def switch_company(self, user_id: uuid.UUID, company_id: uuid.UUID) -> AccessTokenResponse:
        user = await self._user_repo.get_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)

        role_entry: UserCompanyRole | None = next(
            (r for r in user.company_roles if r.company_id == company_id and r.is_active),
            None,
        )
        if role_entry is None:
            raise PermissionDeniedError("No active role for this company")

        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            company_id=company_id,
            role=role_entry.role.value,
            warehouse_id=role_entry.warehouse_id,
        )
        return AccessTokenResponse(access_token=access_token)

    async def refresh(self, raw_token: str) -> AccessTokenResponse:
        token_hash = hash_token(raw_token)
        token_record = await self._token_repo.get_valid_by_hash(token_hash)
        if token_record is None:
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self._user_repo.get_with_roles(token_record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        await self._token_repo.revoke(token_record)

        company_id = token_record.company_id
        role: UserRole | None = None
        warehouse_id: uuid.UUID | None = None
        if company_id:
            role_entry = next(
                (r for r in user.company_roles if r.company_id == company_id and r.is_active),
                None,
            )
            if role_entry:
                role = role_entry.role
                warehouse_id = role_entry.warehouse_id

        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            company_id=company_id,
            role=role.value if role else None,
            warehouse_id=warehouse_id,
        )
        return AccessTokenResponse(access_token=access_token)

    async def logout(self, raw_token: str) -> None:
        token_hash = hash_token(raw_token)
        token_record = await self._token_repo.get_valid_by_hash(token_hash)
        if token_record:
            await self._token_repo.revoke(token_record)

    async def get_me(self, user_id: uuid.UUID) -> User:
        user = await self._user_repo.get_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return user
