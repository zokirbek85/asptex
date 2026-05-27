import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.shared.enums import UserRole
from app.shared.schemas import AppBaseModel


class UserCreate(AppBaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str | None = Field(None, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    preferred_language: str = Field("uz", pattern=r"^(uz|ru)$")
    is_superadmin: bool = False

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username may only contain letters, digits, underscores, and dots")
        return v.lower()


class UserUpdate(AppBaseModel):
    email: str | None = Field(None, max_length=255)
    full_name: str | None = Field(None, min_length=1, max_length=255)
    preferred_language: str | None = Field(None, pattern=r"^(uz|ru)$")


class UserPasswordChange(AppBaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class UserRoleAssign(AppBaseModel):
    company_id: uuid.UUID
    role: UserRole
    warehouse_id: uuid.UUID | None = None


class UserRoleUpdate(AppBaseModel):
    role: UserRole
    warehouse_id: uuid.UUID | None = None


class UserRoleResponse(AppBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    role: UserRole
    warehouse_id: uuid.UUID | None
    warehouse_name: str | None
    is_active: bool
    created_at: datetime


class UserResponse(AppBaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    full_name: str
    is_active: bool
    is_superadmin: bool
    preferred_language: str
    created_at: datetime
    updated_at: datetime
    roles: list[UserRoleResponse] = []
