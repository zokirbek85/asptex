"""
T4 — guard against the same physical FG being counted twice: once via the
daily report's own PRODUCTION_INBOUND line, and once via a confirmed tolling
distribution's OWNER_NET/PROCESSOR_FEE postings for the same day.
"""
from datetime import date
from decimal import Decimal
import uuid

import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.modules.daily_report.models import DailyReport, DailyReportLine
from app.modules.daily_report.schemas import DailyReportLineCreate, DailyReportSubmit
from app.modules.daily_report.service import DailyReportService
from app.modules.lot.models import Lot
from app.modules.tolling.models import TollingDistribution, TollingLot
from app.modules.tolling.service import TollingService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import (
    LineCategory,
    LotStatus,
    ReportStatus,
    TollingDistributionStatus,
    TollingLotStatus,
    WarehouseType,
)


def _ctx() -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester")


@pytest.mark.asyncio
async def test_daily_report_submit_blocked_when_tolling_distribution_confirmed(
    session, test_company, test_warehouse
):
    """test_warehouse is FINISHED_GOODS (see conftest.py)."""
    lot = Lot(
        company_id=test_company.id, lot_number="2026-100", year=2026,
        sequence_number=100, status=LotStatus.OPEN,
    )
    session.add(lot)
    await session.flush()

    tl = TollingLot(company_id=test_company.id, lot_id=lot.id, status=TollingLotStatus.OPEN)
    session.add(tl)
    await session.flush()

    dist = TollingDistribution(
        company_id=test_company.id,
        tolling_lot_id=tl.id,
        distribution_date=date(2026, 4, 1),
        daily_fg_kg_total=Decimal("1000.000"),
        status=TollingDistributionStatus.CONFIRMED,
        created_by=uuid.uuid4(),
    )
    session.add(dist)
    await session.flush()

    report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 4, 1),
        status=ReportStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(report)
    await session.flush()

    svc = DailyReportService(session)
    data = DailyReportSubmit(lines=[
        DailyReportLineCreate(
            line_category=LineCategory.PRODUCTION_INBOUND,
            quantity_kg=Decimal("500"),
        ),
    ])
    with pytest.raises(BusinessRuleViolationError):
        await svc.submit(report.id, test_company.id, data, _ctx())


@pytest.mark.asyncio
async def test_tolling_confirm_blocked_when_dr_has_production_inbound(
    session, test_company, test_warehouse
):
    """Reverse direction: DR already submitted with PRODUCTION_INBOUND for the
    same FG warehouse/date should block confirming a DRAFT distribution."""
    report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 4, 2),
        status=ReportStatus.SUBMITTED,
        created_by=uuid.uuid4(),
    )
    session.add(report)
    await session.flush()
    session.add(DailyReportLine(
        daily_report_id=report.id,
        line_number=1,
        line_category=LineCategory.PRODUCTION_INBOUND,
        quantity_kg=Decimal("300.000"),
    ))
    await session.flush()

    lot = Lot(
        company_id=test_company.id, lot_number="2026-101", year=2026,
        sequence_number=101, status=LotStatus.OPEN,
    )
    session.add(lot)
    await session.flush()

    tl = TollingLot(company_id=test_company.id, lot_id=lot.id, status=TollingLotStatus.OPEN)
    session.add(tl)
    await session.flush()

    dist = TollingDistribution(
        company_id=test_company.id,
        tolling_lot_id=tl.id,
        distribution_date=date(2026, 4, 2),
        daily_fg_kg_total=Decimal("300.000"),
        status=TollingDistributionStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(dist)
    await session.flush()

    svc = TollingService(session)
    with pytest.raises(BusinessRuleViolationError):
        await svc.confirm_distribution(dist.id, test_company.id, _ctx())


@pytest.mark.asyncio
async def test_daily_report_submit_allowed_when_no_tolling_conflict(
    session, test_company, test_warehouse
):
    """Sanity: production inbound submits fine when no tolling lot is open."""
    report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 4, 3),
        status=ReportStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(report)
    await session.flush()

    svc = DailyReportService(session)
    data = DailyReportSubmit(lines=[
        DailyReportLineCreate(
            line_category=LineCategory.PRODUCTION_INBOUND,
            quantity_kg=Decimal("500"),
        ),
    ])
    updated_report, tolling_warnings, _stock_warnings = await svc.submit(
        report.id, test_company.id, data, _ctx()
    )
    assert updated_report.status == ReportStatus.SUBMITTED
    assert tolling_warnings is None
