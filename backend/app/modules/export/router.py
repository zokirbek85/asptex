from datetime import date
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.dependencies import AdminDep, CurrentUserDep, SessionDep
from app.modules.export.service import ExportService
from app.shared.enums import WarehouseType

router = APIRouter(prefix="/export", tags=["export"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF = "application/pdf"


def _media_type(fmt: str) -> str:
    return _PDF if fmt == "pdf" else _XLSX


def _ext(fmt: str) -> str:
    return "pdf" if fmt == "pdf" else "xlsx"


@router.get("/stock-report")
async def export_stock_report(
    session: SessionDep,
    current_user: CurrentUserDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    warehouse_type: WarehouseType | None = Query(None),
    as_of_date: date | None = Query(None),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_stock_report(
            current_user.company_id, fmt, warehouse_type, as_of_date
        )
    return Response(
        content=data,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="stock-report.{_ext(fmt)}"'},
    )


@router.get("/shipments")
async def export_shipments(
    session: SessionDep,
    current_user: CurrentUserDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    buyer_id: uuid.UUID | None = Query(None),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_shipments(
            current_user.company_id, fmt, date_from, date_to, buyer_id
        )
    return Response(
        content=data,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="shipments.{_ext(fmt)}"'},
    )


@router.get("/daily-report/{report_id}")
async def export_daily_report(
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_daily_report(current_user.company_id, report_id, fmt)
    return Response(
        content=data,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="daily-report.{_ext(fmt)}"'},
    )


@router.get("/lot-card/{lot_id}")
async def export_lot_card(
    lot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_lot_card(current_user.company_id, lot_id, fmt)
    return Response(
        content=data,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="lot-card.{_ext(fmt)}"'},
    )


@router.get("/waste-report")
async def export_waste_report(
    session: SessionDep,
    current_user: CurrentUserDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_waste_report(
            current_user.company_id, fmt, date_from, date_to
        )
    return Response(
        content=data,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="waste-report.{_ext(fmt)}"'},
    )


@router.get("/audit-log")
async def export_audit_log(
    session: SessionDep,
    current_user: AdminDep,
    fmt: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    entity_type: str | None = Query(None),
) -> Response:
    async with session.begin():
        svc = ExportService(session)
        data = await svc.export_audit_log(
            current_user.company_id, fmt, date_from, date_to, entity_type
        )
    return Response(
        content=data,
        media_type=_XLSX,
        headers={"Content-Disposition": 'attachment; filename="audit-log.xlsx"'},
    )
