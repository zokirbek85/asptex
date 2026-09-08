import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.shared.enums import CompanyType, UserRole
from app.shared.schemas import AppBaseModel


# ── Request schemas ───────────────────────────────────────────────────────────

class LoginRequest(AppBaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class SwitchCompanyRequest(AppBaseModel):
    company_id: uuid.UUID


class ChangePasswordRequest(AppBaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Response schemas ──────────────────────────────────────────────────────────

class CompanyBrief(AppBaseModel):
    id: uuid.UUID
    name: str
    short_name: str | None
    role: UserRole
    company_type: CompanyType


class UserResponse(AppBaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    full_name: str
    is_active: bool
    is_superadmin: bool
    preferred_language: str
    created_at: datetime


class TokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    companies: list[CompanyBrief]


class AccessTokenResponse(AppBaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(AppBaseModel):
    refresh_token: str


class MeResponse(AppBaseModel):
    user: UserResponse
    company_id: uuid.UUID | None
    role: UserRole | None
    warehouse_id: uuid.UUID | None
