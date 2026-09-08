from pydantic import Field

from app.shared.schemas import AppBaseModel

# Canonical execution order — later modules depend on earlier ones being cleared first.
DATA_RESET_MODULES: list[str] = [
    "tolling",
    "shipments",
    "adjustments",
    "opening_balance",
    "daily_reports",
    "stock_transactions",
    "lots",
]


class DataResetRequest(AppBaseModel):
    modules: list[str] = Field(..., min_length=1)
    confirm_company_name: str = Field(..., min_length=1)


class DataResetResponse(AppBaseModel):
    modules_cleared: list[str]
    deleted_counts: dict[str, int]
