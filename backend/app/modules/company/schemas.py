import uuid
from datetime import datetime

from pydantic import Field

from app.shared.enums import CompanyType
from app.shared.schemas import AppBaseModel


class CompanyCreate(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=50)
    tax_id: str | None = Field(None, max_length=50)
    address: str | None = None
    company_type: CompanyType


class CompanyUpdate(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=50)
    tax_id: str | None = Field(None, max_length=50)
    address: str | None = None
    company_type: CompanyType | None = None


class CompanyResponse(AppBaseModel):
    id: uuid.UUID
    name: str
    short_name: str | None
    tax_id: str | None
    address: str | None
    company_type: CompanyType
    is_active: bool
    created_at: datetime
    updated_at: datetime
