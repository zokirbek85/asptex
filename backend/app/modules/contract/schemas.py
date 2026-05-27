import uuid
from datetime import date, datetime

from pydantic import Field

from app.shared.schemas import AppBaseModel


class ContractCreate(AppBaseModel):
    contract_number: str = Field(..., min_length=1, max_length=100)
    contract_date: date
    counterparty_id: uuid.UUID
    description: str | None = None


class ContractUpdate(AppBaseModel):
    contract_number: str | None = Field(None, min_length=1, max_length=100)
    contract_date: date | None = None
    description: str | None = None


class ContractResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    contract_number: str
    contract_date: date
    counterparty_id: uuid.UUID
    counterparty_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
