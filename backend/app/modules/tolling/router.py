from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from app.core.dependencies import AdminDep, AdminOrDeputyDep, CurrentUserDep, SessionDep, require_roles
from app.modules.tolling.schemas import (
    DistributionCreate,
    DistributionOut,
    DistributionUpdate,
    LotStockSummaryOut,
    LotSummaryOut,
    DailyRegisterOut,
    ParticipantAdd,
    ParticipantOut,
    ParticipantUpdate,
    TollingLotClose,
    TollingLotCreate,
    TollingLotOut,
)
from app.modules.tolling.service import TollingService
from app.shared.enums import TollingDistributionStatus, UserRole
from app.shared.schemas import PaginatedResponse
from typing import Annotated
from fastapi import Depends

router = APIRouter(prefix="/tolling", tags=["tolling"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

TollingViewDep = Annotated[
    object,
    Depends(require_roles(
        UserRole.ADMIN, UserRole.DIRECTOR, UserRole.DEPUTY_DIRECTOR,
        UserRole.ACCOUNTANT, UserRole.WH_FINISHED,
    )),
]

TollingWriteDep = Annotated[
    object,
    Depends(require_roles(
        UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR, UserRole.ACCOUNTANT, UserRole.WH_FINISHED,
    )),
]

TollingConfirmDep = Annotated[
    object,
    Depends(require_roles(UserRole.ADMIN, UserRole.DEPUTY_DIRECTOR, UserRole.ACCOUNTANT)),
]


def _ctx(request: Request, cu):
    return cu.to_audit_context(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


# ── Lots ──────────────────────────────────────────────────────────────────────

@router.post("/lots", response_model=TollingLotOut, status_code=status.HTTP_201_CREATED)
async def create_lot(
    body: TollingLotCreate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> TollingLotOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.create_lot(current_user.company_id, body, _ctx(request, current_user))


@router.get("/lots/active")
async def get_active_lot(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TollingLotOut | None:
    async with session.begin():
        svc = TollingService(session)
        return await svc.get_active_lot(current_user.company_id)


@router.get("/lots/{lot_id}", response_model=TollingLotOut)
async def get_lot(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TollingLotOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.get_lot(lot_id)


@router.get("/lots/{lot_id}/stock-summary", response_model=LotStockSummaryOut)
async def lot_stock_summary(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LotStockSummaryOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.get_lot_stock_summary(current_user.company_id, lot_id)


@router.post("/lots/{lot_id}/close", response_model=TollingLotOut)
async def close_lot(
    lot_id: uuid.UUID,
    body: TollingLotClose,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> TollingLotOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.close_lot(lot_id, body, _ctx(request, current_user))


# ── Participants ──────────────────────────────────────────────────────────────

@router.post("/lots/{lot_id}/participants", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
async def add_participant(
    lot_id: uuid.UUID,
    body: ParticipantAdd,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ParticipantOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.add_participant(lot_id, body, _ctx(request, current_user))


@router.patch("/lots/{lot_id}/participants/{participant_id}", response_model=ParticipantOut)
async def update_participant(
    lot_id: uuid.UUID,
    participant_id: uuid.UUID,
    body: ParticipantUpdate,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> ParticipantOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.update_participant(lot_id, participant_id, body, _ctx(request, current_user))


@router.delete("/lots/{lot_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(
    lot_id: uuid.UUID,
    participant_id: uuid.UUID,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> None:
    async with session.begin():
        svc = TollingService(session)
        await svc.remove_participant(lot_id, participant_id)


# ── Distributions ─────────────────────────────────────────────────────────────

@router.post("/distributions", response_model=DistributionOut, status_code=status.HTTP_201_CREATED)
async def create_distribution(
    body: DistributionCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.create_distribution(current_user.company_id, body, _ctx(request, current_user))


@router.get("/distributions", response_model=PaginatedResponse[DistributionOut])
async def list_distributions(
    session: SessionDep,
    current_user: CurrentUserDep,
    tolling_lot_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: TollingDistributionStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    async with session.begin():
        svc = TollingService(session)
        return await svc.list_distributions(
            current_user.company_id, tolling_lot_id, date_from, date_to, status, page, page_size
        )


@router.get("/distributions/{dist_id}", response_model=DistributionOut)
async def get_distribution(
    dist_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.get_distribution(dist_id)


@router.patch("/distributions/{dist_id}", response_model=DistributionOut)
async def update_distribution(
    dist_id: uuid.UUID,
    body: DistributionUpdate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.update_distribution(dist_id, body, _ctx(request, current_user))


@router.post("/distributions/{dist_id}/preview", response_model=DistributionOut)
async def preview_distribution(
    dist_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.preview_distribution(dist_id)


@router.post("/distributions/{dist_id}/confirm", response_model=DistributionOut)
async def confirm_distribution(
    dist_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.confirm_distribution(dist_id, _ctx(request, current_user))


@router.post("/distributions/{dist_id}/unconfirm", response_model=DistributionOut)
async def unconfirm_distribution(
    dist_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> DistributionOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.unconfirm_distribution(dist_id, _ctx(request, current_user))


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/lot-summary/{lot_id}", response_model=LotSummaryOut)
async def lot_summary(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LotSummaryOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.lot_summary(current_user.company_id, lot_id)


@router.get("/reports/daily-register", response_model=DailyRegisterOut)
async def daily_register(
    session: SessionDep,
    current_user: CurrentUserDep,
    tolling_lot_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> DailyRegisterOut:
    async with session.begin():
        svc = TollingService(session)
        return await svc.daily_register(current_user.company_id, tolling_lot_id, date_from, date_to)


# ── Excel exports ─────────────────────────────────────────────────────────────

@router.get("/export/lot-summary/{lot_id}")
async def export_lot_summary(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    async with session.begin():
        svc = TollingService(session)
        data = await svc.export_lot_summary_xlsx(current_user.company_id, lot_id)
    return Response(
        content=data,
        media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="tolling-lot-summary-{lot_id}.xlsx"'},
    )


@router.get("/export/daily-register")
async def export_daily_register(
    session: SessionDep,
    current_user: CurrentUserDep,
    tolling_lot_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> Response:
    async with session.begin():
        svc = TollingService(session)
        data = await svc.export_daily_register_xlsx(current_user.company_id, tolling_lot_id, date_from, date_to)
    return Response(
        content=data,
        media_type=_XLSX,
        headers={"Content-Disposition": 'attachment; filename="tolling-daily-register.xlsx"'},
    )
