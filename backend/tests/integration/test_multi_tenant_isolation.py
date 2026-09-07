"""
T1 — multi-tenant isolation (IDOR) regression tests.

Each test builds a row that belongs to `test_company` (company A) and then
calls the service method with a *different* company's id (company B),
asserting the row is treated as not found (404-equivalent NotFoundError).
A second assertion confirms the correct-company path still works.
"""
from datetime import date
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.adjustment.models import InventoryAdjustment
from app.modules.adjustment.service import AdjustmentService
from app.modules.company.models import Company
from app.modules.counterparty.models import Counterparty
from app.modules.daily_report.models import DailyReport
from app.modules.daily_report.service import DailyReportService
from app.modules.lot.models import Lot
from app.modules.opening_balance.models import OpeningBalanceEntry
from app.modules.opening_balance.service import OpeningBalanceService
from app.modules.shipment.models import Shipment
from app.modules.shipment.service import ShipmentService
from app.modules.tolling.models import TollingDistribution, TollingLot
from app.modules.tolling.service import TollingService
from app.modules.warehouse.models import Warehouse
from app.shared.enums import (
    AdjustmentStatus,
    CounterpartyType,
    LotStatus,
    ReportStatus,
    ShipmentStatus,
    TollingDistributionStatus,
    TollingLotStatus,
    WarehouseType,
)


@pytest_asyncio.fixture
async def company_b(session: AsyncSession) -> Company:
    company = Company(name="Other Company", short_name="OC", tax_id="TEST-002")
    session.add(company)
    await session.flush()
    return company


@pytest.mark.asyncio
async def test_shipment_get_cross_tenant_404(session, test_company, test_warehouse, company_b):
    cp = Counterparty(
        company_id=test_company.id, name="Buyer A", counterparty_type=CounterpartyType.BUYER
    )
    session.add(cp)
    await session.flush()

    shipment = Shipment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        shipment_number="2026-000001",
        shipment_date=date.today(),
        status=ShipmentStatus.ACTIVE,
        buyer_id=cp.id,
        created_by=uuid.uuid4(),
    )
    session.add(shipment)
    await session.flush()

    svc = ShipmentService(session)
    with pytest.raises(NotFoundError):
        await svc.get(shipment.id, company_b.id)

    fetched = await svc.get(shipment.id, test_company.id)
    assert fetched.id == shipment.id


@pytest.mark.asyncio
async def test_daily_report_get_cross_tenant_404(session, test_company, test_warehouse, company_b):
    report = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date.today(),
        status=ReportStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(report)
    await session.flush()

    svc = DailyReportService(session)
    with pytest.raises(NotFoundError):
        await svc.get(report.id, company_b.id)

    fetched = await svc.get(report.id, test_company.id)
    assert fetched.id == report.id


@pytest.mark.asyncio
async def test_adjustment_get_cross_tenant_404(session, test_company, test_warehouse, company_b):
    adj = InventoryAdjustment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        adjustment_number="ADJ-000001",
        adjustment_date=date.today(),
        reason="Test",
        status=AdjustmentStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(adj)
    await session.flush()

    svc = AdjustmentService(session)
    with pytest.raises(NotFoundError):
        await svc.get(adj.id, company_b.id)

    fetched = await svc.get(adj.id, test_company.id)
    assert fetched.id == adj.id


@pytest.mark.asyncio
async def test_opening_balance_get_cross_tenant_404(session, test_company, test_warehouse, company_b):
    entry = OpeningBalanceEntry(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        balance_date=date.today(),
        status=AdjustmentStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(entry)
    await session.flush()

    svc = OpeningBalanceService(session)
    with pytest.raises(NotFoundError):
        await svc.get(entry.id, company_b.id)

    fetched = await svc.get(entry.id, test_company.id)
    assert fetched.id == entry.id


@pytest.mark.asyncio
async def test_tolling_get_lot_cross_tenant_404(session, test_company, company_b):
    lot = Lot(
        company_id=test_company.id,
        lot_number="2026-001",
        year=2026,
        sequence_number=1,
        status=LotStatus.OPEN,
    )
    session.add(lot)
    await session.flush()

    tl = TollingLot(
        company_id=test_company.id,
        lot_id=lot.id,
        status=TollingLotStatus.OPEN,
    )
    session.add(tl)
    await session.flush()

    svc = TollingService(session)
    with pytest.raises(NotFoundError):
        await svc.get_lot(tl.id, company_b.id)

    fetched = await svc.get_lot(tl.id, test_company.id)
    assert fetched.id == tl.id


@pytest.mark.asyncio
async def test_tolling_get_distribution_cross_tenant_404(session, test_company, company_b):
    lot = Lot(
        company_id=test_company.id,
        lot_number="2026-002",
        year=2026,
        sequence_number=2,
        status=LotStatus.OPEN,
    )
    session.add(lot)
    await session.flush()

    tl = TollingLot(company_id=test_company.id, lot_id=lot.id, status=TollingLotStatus.OPEN)
    session.add(tl)
    await session.flush()

    dist = TollingDistribution(
        company_id=test_company.id,
        tolling_lot_id=tl.id,
        distribution_date=date.today(),
        daily_fg_kg_total=100.0,
        status=TollingDistributionStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(dist)
    await session.flush()

    svc = TollingService(session)
    with pytest.raises(NotFoundError):
        await svc.get_distribution(dist.id, company_b.id)

    fetched = await svc.get_distribution(dist.id, test_company.id)
    assert fetched.id == dist.id
