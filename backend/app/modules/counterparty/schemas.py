import uuid
from datetime import datetime

from pydantic import Field

from app.shared.enums import CounterpartyType
from app.shared.schemas import AppBaseModel


class ContactCreate(AppBaseModel):
    contact_type: str = Field(..., pattern=r"^(PHONE|EMAIL|TELEGRAM|OTHER)$")
    contact_value: str = Field(..., min_length=1, max_length=255)
    label: str | None = Field(None, max_length=100)
    is_primary: bool = False


class ContactResponse(AppBaseModel):
    id: uuid.UUID
    contact_type: str
    contact_value: str
    label: str | None
    is_primary: bool


class CounterpartyCreate(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    tax_id: str | None = Field(None, max_length=100)
    counterparty_type: CounterpartyType = CounterpartyType.BUYER
    notes: str | None = None
    contacts: list[ContactCreate] = []


class CounterpartyUpdate(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    tax_id: str | None = Field(None, max_length=100)
    counterparty_type: CounterpartyType | None = None
    notes: str | None = None


class CounterpartyMerge(AppBaseModel):
    source_id: uuid.UUID
    reason: str | None = None


class CounterpartyResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    short_name: str | None
    country: str | None
    tax_id: str | None
    counterparty_type: CounterpartyType
    notes: str | None
    is_active: bool
    merged_into_id: uuid.UUID | None
    contacts: list[ContactResponse] = []
    created_at: datetime
    updated_at: datetime
