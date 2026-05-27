import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.shared.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


# ── JWT extraction ───────────────────────────────────────────────────────────

def _get_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Authentication required", "code": "NOT_AUTHENTICATED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _decode_token(token: str) -> dict:
    try:
        return decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or expired token", "code": "TOKEN_INVALID"},
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current user context ─────────────────────────────────────────────────────

class CurrentUser:
    """Lightweight user context extracted from the JWT — no DB hit."""

    def __init__(self, payload: dict):
        self.user_id: uuid.UUID = uuid.UUID(payload["sub"])
        raw_company = payload.get("company_id")
        self.company_id: uuid.UUID | None = uuid.UUID(raw_company) if raw_company else None
        self.role: UserRole | None = UserRole(payload["role"]) if payload.get("role") else None
        raw_wh = payload.get("warehouse_id")
        self.warehouse_id: uuid.UUID | None = uuid.UUID(raw_wh) if raw_wh else None


async def get_current_user(
    token: Annotated[str, Depends(_get_token)],
) -> CurrentUser:
    payload = _decode_token(token)
    return CurrentUser(payload)


async def get_current_user_with_company(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No company selected — call /auth/switch-company first", "code": "NO_COMPANY_SELECTED"},
        )
    return current_user


# ── Role enforcement ─────────────────────────────────────────────────────────

def require_roles(*roles: UserRole):
    """Dependency factory: ensures current user has one of the specified roles."""

    async def checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user_with_company)],
    ) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "Insufficient permissions", "code": "PERMISSION_DENIED"},
            )
        return current_user

    return checker


# ── Pre-built role deps ───────────────────────────────────────────────────────

RequireAdmin = Depends(require_roles(UserRole.ADMIN))
RequireAdminOrDeputy = Depends(require_roles(UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR))
RequireManagement = Depends(require_roles(
    UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR, UserRole.DIRECTOR,
))
RequireAnyRole = Depends(get_current_user_with_company)

# ── Session shorthand ─────────────────────────────────────────────────────────

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_with_company)]
