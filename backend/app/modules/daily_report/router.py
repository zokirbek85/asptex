from datetime import date
import uuid

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import func, select

from app.core.dependencies import AdminDep, AdminOrDeputyDep, CurrentUserDep, SessionDep
from app.modules.daily_report.schemas import (
    DailyReportCreate,
    DailyReportLineResponse,
    DailyReportResponse,
    DailyReportReopen,
    DailyReportSubmit,
    OpeningBalanceLine,
    TollingWarning,
    WarehouseRunningBalance,
)
from app.modules.daily_report.service import DailyReportService
from app.shared.enums import ReportStatus
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/daily-reports", tags=["daily-reports"])


def _ctx(request: Request, cu):
    return cu.to_audit_context(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


def _build(
    report,
    opening_balance: list[OpeningBalanceLine] | None = None,
    tolling_warnings: list[TollingWarning] | None = None,
) -> DailyReportResponse:
    return DailyReportResponse(
        id=report.id,
        company_id=report.company_id,
        warehouse_id=report.warehouse_id,
        report_date=report.report_date,
        status=report.status,
        opening_balance=opening_balance or [],
        lines=[
            DailyReportLineResponse(
                id=line.id,
                line_number=line.line_number,
                line_category=line.line_category,
                lot_id=line.lot_id,
                count_id=line.count_id,
                owner_id=line.owner_id,
                waste_type=line.waste_type,
                buyer_id=line.buyer_id,
                pkg_item_type=line.pkg_item_type,
                quantity_kg=line.quantity_kg,
                quantity_bags=line.quantity_bags,
                quantity_kip=line.quantity_kip,
                quantity_units=line.quantity_units,
                notes=line.notes,
                transaction_id=line.transaction_id,
            )
            for line in (report.lines or [])
        ],
        submitted_at=report.submitted_at,
        submitted_by=report.submitted_by,
        closed_at=report.closed_at,
        closed_by=report.closed_by,
        reopen_count=report.reopen_count or 0,
        notes=report.notes,
        created_at=report.created_at,
        tolling_warnings=tolling_warnings,
    )


@router.get("/", response_model=PaginatedResponse[DailyReportResponse])
async def list_reports(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: ReportStatus | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> PaginatedResponse[DailyReportResponse]:
    async with session.begin():
        svc = DailyReportService(session)
        result = await svc.list(
            current_user.company_id,
            warehouse_id,
            page, page_size, status, date_from, date_to,
        )
    return PaginatedResponse[DailyReportResponse].build(
        [_build(r) for r in result.items],
        result.total, result.page, result.page_size,
    )


@router.get("/fg-total")
async def get_fg_production_total(
    session: SessionDep,
    current_user: CurrentUserDep,
    report_date: date = Query(...),
) -> dict:
    from app.modules.daily_report.models import DailyReport, DailyReportLine
    from app.modules.warehouse.models import Warehouse
    from app.shared.enums import WarehouseType, LineCategory, ReportStatus

    async with session.begin():
        result = await session.execute(
            select(func.coalesce(func.sum(DailyReportLine.quantity_kg), 0))
            .join(DailyReport, DailyReportLine.daily_report_id == DailyReport.id)
            .join(Warehouse, Warehouse.id == DailyReport.warehouse_id)
            .where(
                DailyReport.company_id == current_user.company_id,
                DailyReport.report_date == report_date,
                DailyReport.status.in_([ReportStatus.SUBMITTED, ReportStatus.CLOSED]),
                Warehouse.warehouse_type == WarehouseType.FINISHED_GOODS,
                DailyReportLine.line_category == LineCategory.PRODUCTION_INBOUND,
            )
        )
        total_kg = float(result.scalar_one() or 0)
    return {"date": str(report_date), "total_kg": total_kg}


@router.get("/lookup", response_model=DailyReportResponse | None)
async def lookup_report(
    session: SessionDep,
    current_user: CurrentUserDep,
    warehouse_id: uuid.UUID = Query(...),
    report_date: date = Query(...),
) -> DailyReportResponse | None:
    async with session.begin():
        svc = DailyReportService(session)
        existing = await svc.repo.get_by_warehouse_date(
            current_user.company_id, warehouse_id, report_date
        )
        if existing is None:
            return None
        report = await svc.repo.get_with_lines(existing.id)
        opening = await svc.get_opening_balance(
            current_user.company_id, warehouse_id, report_date
        )
    return _build(report, opening)


@router.post("/", response_model=DailyReportResponse, status_code=status.HTTP_200_OK)
async def create_or_get_report(
    body: DailyReportCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report = await svc.get_or_create(current_user.company_id, body, _ctx(request, current_user))
        opening = await svc.get_opening_balance(
            current_user.company_id, body.warehouse_id, body.report_date
        )
    return _build(report, opening)


@router.get("/{report_id}", response_model=DailyReportResponse)
async def get_report(
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report = await svc.get(report_id)
        opening = await svc.get_opening_balance(
            current_user.company_id, report.warehouse_id, report.report_date
        )
    return _build(report, opening)


@router.put("/{report_id}/lines", response_model=DailyReportResponse)
async def update_lines(
    report_id: uuid.UUID,
    body: DailyReportSubmit,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report = await svc.update_lines(report_id, body, _ctx(request, current_user))
        opening = await svc.get_opening_balance(
            current_user.company_id, report.warehouse_id, report.report_date
        )
    return _build(report, opening)


@router.post("/{report_id}/submit", response_model=DailyReportResponse)
async def submit_report(
    report_id: uuid.UUID,
    body: DailyReportSubmit,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report, tolling_warnings = await svc.submit(report_id, body, _ctx(request, current_user))
        opening = await svc.get_opening_balance(
            current_user.company_id, report.warehouse_id, report.report_date
        )
    return _build(report, opening, tolling_warnings)


@router.post("/{report_id}/close", response_model=DailyReportResponse)
async def close_report(
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report = await svc.close(report_id, _ctx(request, current_user))
    return _build(report)


@router.post("/{report_id}/reopen", response_model=DailyReportResponse)
async def reopen_report(
    report_id: uuid.UUID,
    body: DailyReportReopen,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> DailyReportResponse:
    async with session.begin():
        svc = DailyReportService(session)
        report = await svc.reopen(report_id, body, _ctx(request, current_user))
        opening = await svc.get_opening_balance(
            current_user.company_id, report.warehouse_id, report.report_date
        )
    return _build(report, opening)


@router.get("/warehouses/{warehouse_id}/running-balance", response_model=WarehouseRunningBalance)
async def get_running_balance(
    warehouse_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = Query(None, description="YYYY-MM-DD, bo'sh bo'lsa bugungi sana"),
) -> WarehouseRunningBalance:
    async with session.begin():
        svc = DailyReportService(session)
        return await svc.get_warehouse_running_balance(
            company_id=current_user.company_id,
            warehouse_id=warehouse_id,
            as_of_date=as_of_date,
        )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft_report(
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: AdminOrDeputyDep,
) -> None:
    async with session.begin():
        svc = DailyReportService(session)
        await svc.delete_draft(report_id, _ctx(request, current_user))
