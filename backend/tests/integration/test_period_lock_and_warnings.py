"""
T2 — period lock (closed-day posting block) and negative-stock warning
surfacing regression tests.
"""
from datetime import date
from decimal import Decimal
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError
from app.modules.adjustment.models import InventoryAdjustment, InventoryAdjustmentLine
from app.modules.adjustment.service import AdjustmentService
from app.modules.company.models import Company
from app.modules.count_catalog.models import CountCatalog
from app.modules.counterparty.models import Counterparty
from app.modules.daily_report.models import DailyReport
from app.modules.daily_report.schemas import DailyReportLineCreate, DailyReportSubmit
from app.modules.daily_report.service import DailyReportService
from app.modules.lot.models import Lot
from app.modules.shipment.models import Shipment, ShipmentLine
from app.modules.shipment.schemas import ShipmentLineCancelRequest
from app.modules.shipment.service import ShipmentService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import (
    AdjustmentStatus,
    CounterpartyType,
    LineCategory,
    LotStatus,
    ReportStatus,
    ShipmentStatus,
    WarehouseType,
)


def _ctx() -> AuditContext:
    return AuditContext(
        actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester"
    )


@pytest.mark.asyncio
async def test_adjustment_post_blocked_on_closed_period(session, test_company, test_warehouse):
    closed_report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 1, 10),
        status=ReportStatus.CLOSED,
        created_by=uuid.uuid4(),
    )
    session.add(closed_report)
    await session.flush()

    adj = InventoryAdjustment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        adjustment_number="ADJ-000002",
        adjustment_date=date(2026, 1, 10),
        reason="Test",
        status=AdjustmentStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(adj)
    await session.flush()
    session.add(InventoryAdjustmentLine(
        adjustment_id=adj.id,
        line_number=1,
        quantity_kg_before=0,
        quantity_kg_after=10,
    ))
    await session.flush()
    await session.refresh(adj, attribute_names=["lines"])

    svc = AdjustmentService(session)
    with pytest.raises(BusinessRuleViolationError):
        await svc.post(adj.id, test_company.id, _ctx())


@pytest.mark.asyncio
async def test_shipment_cancel_blocked_on_closed_period(session, test_company, test_warehouse):
    closed_report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 1, 11),
        status=ReportStatus.CLOSED,
        created_by=uuid.uuid4(),
    )
    session.add(closed_report)
    await session.flush()

    cp = Counterparty(
        company_id=test_company.id, name="Buyer X", counterparty_type=CounterpartyType.BUYER
    )
    lot = Lot(
        company_id=test_company.id,
        lot_number="2026-010",
        year=2026,
        sequence_number=10,
        status=LotStatus.OPEN,
    )
    count = CountCatalog(company_id=test_company.id, count_value="30/1")
    session.add_all([cp, lot, count])
    await session.flush()

    shipment = Shipment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        shipment_number="2026-000099",
        shipment_date=date(2026, 1, 11),
        status=ShipmentStatus.ACTIVE,
        buyer_id=cp.id,
        created_by=uuid.uuid4(),
    )
    session.add(shipment)
    await session.flush()
    line = ShipmentLine(
        shipment_id=shipment.id,
        lot_id=lot.id,
        count_id=count.id,
        owner_id=cp.id,
        quantity_kg=100,
        cancelled_kg=0,
        cancelled_bags=0,
        is_fully_cancelled=False,
        line_number=1,
    )
    session.add(line)
    await session.flush()

    svc = ShipmentService(session)
    with pytest.raises(BusinessRuleViolationError):
        await svc.cancel_line(
            shipment.id,
            test_company.id,
            line.id,
            ShipmentLineCancelRequest(quantity_kg=Decimal("10"), reason="test cancel"),
            _ctx(),
        )


@pytest.mark.asyncio
async def test_daily_report_submit_surfaces_negative_stock_warning(
    session, test_company, test_warehouse
):
    report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 2, 1),
        status=ReportStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(report)
    await session.flush()

    svc = DailyReportService(session)
    data = DailyReportSubmit(lines=[
        DailyReportLineCreate(
            line_category=LineCategory.PRODUCTION_ISSUE,
            quantity_kg=Decimal("50"),
        ),
    ])
    updated_report, tolling_warnings, stock_warnings = await svc.submit(
        report.id, test_company.id, data, _ctx()
    )

    assert updated_report.status == ReportStatus.SUBMITTED
    assert stock_warnings is not None
    assert len(stock_warnings) == 1
    assert stock_warnings[0].current_kg == Decimal("0")
    assert stock_warnings[0].after_kg == Decimal("-50")
