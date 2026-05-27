import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import PermissionDeniedError
from app.core.security import decode_access_token
from app.shared.base_service import AuditContext
from app.shared.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


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


class CurrentUser:
    """Lightweight user context extracted from the JWT — no DB hit required."""

    def __init__(self, payload: dict):
        self.user_id: uuid.UUID = uuid.UUID(payload["sub"])
        self.username: str = payload.get("username", "")
        self.full_name: str = payload.get("full_name", "")
        raw_company = payload.get("company_id")
        self.company_id: uuid.UUID | None = uuid.UUID(raw_company) if raw_company else None
        self.role: UserRole | None = UserRole(payload["role"]) if payload.get("role") else None
        raw_wh = payload.get("warehouse_id")
        self.warehouse_id: uuid.UUID | None = uuid.UUID(raw_wh) if raw_wh else None

    def to_audit_context(
        self,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditContext:
        return AuditContext(
            actor_id=self.user_id,
            actor_username=self.username,
            actor_full_name=self.full_name,
            company_id=self.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )


def _audit_context_from_request(request: Request, current_user: "CurrentUser") -> AuditContext:
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    return current_user.to_audit_context(
        ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )


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
            detail={
                "detail": "No company selected — call /auth/switch-company first",
                "code": "NO_COMPANY_SELECTED",
            },
        )
    return current_user


def require_roles(*roles: UserRole):
    """Dependency factory: ensures the current user holds one of the given roles."""
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

def AdminRequired(
    cu: Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN))],
) -> CurrentUser:
    return cu


def AdminOrDeputyRequired(
    cu: Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR))],
) -> CurrentUser:
    return cu


def ManagementRequired(
    cu: Annotated[CurrentUser, Depends(
        require_roles(UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR, UserRole.DIRECTOR)
    )],
) -> CurrentUser:
    return cu


# ── Type aliases ──────────────────────────────────────────────────────────────

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_with_company)]
AdminDep = Annotated[CurrentUser, Depends(AdminRequired)]
AdminOrDeputyDep = Annotated[CurrentUser, Depends(AdminOrDeputyRequired)]
