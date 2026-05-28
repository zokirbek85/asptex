from datetime import date
import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, SessionDep
from app.modules.packaging.schemas import (
    MinStockAlert,
    PackagingMovementItem,
    PackagingStockItem,
)
from app.modules.packaging.service import PackagingService
from app.shared.enums import PackagingItemType
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/packaging", tags=["packaging"])


@router.get("/stock", response_model=list[PackagingStockItem])
async def get_stock(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[PackagingStockItem]:
    async with session.begin():
        svc = PackagingService(session)
        return await svc.get_stock(current_user.company_id, warehouse_id)


@router.get("/movements", response_model=PaginatedResponse[PackagingMovementItem])
async def get_movements(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    pkg_item_type: PackagingItemType | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[PackagingMovementItem]:
    async with session.begin():
        svc = PackagingService(session)
        return await svc.get_movements(
            current_user.company_id, warehouse_id,
            pkg_item_type, date_from, date_to, page, page_size,
        )


@router.get("/min-stock-alerts", response_model=list[MinStockAlert])
async def min_stock_alerts(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[MinStockAlert]:
    async with session.begin():
        svc = PackagingService(session)
        return await svc.get_min_stock_alerts(current_user.company_id, warehouse_id)
