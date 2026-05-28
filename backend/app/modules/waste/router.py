from datetime import date
import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.waste.schemas import (
    WasteMovementItem,
    WasteSalesReportItem,
    WasteStockItem,
)
from app.modules.waste.service import WasteService
from app.shared.enums import TransactionType, WasteType
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/waste", tags=["waste"])


@router.get("/stock", response_model=list[WasteStockItem])
async def get_stock(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[WasteStockItem]:
    async with session.begin():
        svc = WasteService(session)
        return await svc.get_stock(current_user.company_id, warehouse_id)


@router.get("/movements", response_model=PaginatedResponse[WasteMovementItem])
async def get_movements(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    waste_type: WasteType | None = Query(None),
    transaction_type: TransactionType | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[WasteMovementItem]:
    async with session.begin():
        svc = WasteService(session)
        return await svc.get_movements(
            current_user.company_id, warehouse_id,
            waste_type, date_from, date_to, transaction_type, page, page_size,
        )


@router.get("/sales-report", response_model=list[WasteSalesReportItem])
async def sales_report(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[WasteSalesReportItem]:
    async with session.begin():
        svc = WasteService(session)
        return await svc.get_sales_report(
            current_user.company_id, warehouse_id, date_from, date_to
        )
