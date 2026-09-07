"""
T6 — reopen ordering guard and target-based adjustment posting.
"""
from datetime import date
from decimal import Decimal
import uuid

import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.modules.adjustment.models import InventoryAdjustment, InventoryAdjustmentLine
from app.modules.adjustment.service import AdjustmentService
from app.modules.daily_report.models import DailyReport
from app.modules.daily_report.schemas import DailyReportReopen
from app.modules.daily_report.service import DailyReportService
from app.modules.stock.repository import StockRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AdjustmentStatus, ReportStatus, TransactionType


def _ctx() -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester")


@pytest.mark.asyncio
async def test_adjustment_post_is_target_based_despite_intervening_posting(
    session, test_company, test_warehouse
):
    adj = InventoryAdjustment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        adjustment_number="ADJ-TGT-001",
        adjustment_date=date(2026, 5, 1),
        reason="Target-based test",
        status=AdjustmentStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(adj)
    await session.flush()
    session.add(InventoryAdjustmentLine(
        adjustment_id=adj.id,
        line_number=1,
        quantity_kg_before=Decimal("0.000"),  # stale — captured before the intervening posting
        quantity_kg_after=Decimal("50.000"),
    ))
    await session.flush()

    # Another posting happens in between DRAFT creation and post() — e.g. a
    # daily report or shipment moved the balance to 20 kg.
    stock_repo = StockRepository(session)
    await stock_repo.post_transaction(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        transaction_type=TransactionType.RECEIPT,
        direction=1,
        quantity_kg=Decimal("20.000"),
        transaction_date=date(2026, 4, 30),
        posted_by=uuid.uuid4(),
        reference_type="TEST",
        reference_id=uuid.uuid4(),
    )

    svc = AdjustmentService(session)
    await svc.post(adj.id, test_company.id, _ctx())

    final_balance = await stock_repo.get_balance(
        company_id=test_company.id, warehouse_id=test_warehouse.id,
    )
    assert final_balance == Decimal("50.000")


@pytest.mark.asyncio
async def test_adjustment_post_blocks_negative_target(session, test_company, test_warehouse):
    adj = InventoryAdjustment(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        adjustment_number="ADJ-TGT-002",
        adjustment_date=date(2026, 5, 3),
        reason="Negative target test",
        status=AdjustmentStatus.DRAFT,
        created_by=uuid.uuid4(),
    )
    session.add(adj)
    await session.flush()
    session.add(InventoryAdjustmentLine(
        adjustment_id=adj.id,
        line_number=1,
        quantity_kg_before=Decimal("0.000"),
        quantity_kg_after=Decimal("-5.000"),
    ))
    await session.flush()

    svc = AdjustmentService(session)
    with pytest.raises(BusinessRuleViolationError):
        await svc.post(adj.id, test_company.id, _ctx())


@pytest.mark.asyncio
async def test_reopen_blocked_when_later_day_still_submitted(
    session, test_company, test_warehouse
):
    day1 = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 5, 1),
        status=ReportStatus.SUBMITTED,
        created_by=uuid.uuid4(),
    )
    day2 = DailyReport(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
        report_date=date(2026, 5, 2),
        status=ReportStatus.SUBMITTED,
        created_by=uuid.uuid4(),
    )
    session.add_all([day1, day2])
    await session.flush()

    svc = DailyReportService(session)
    with pytest.raises(BusinessRuleViolationError):
        await svc.reopen(
            day1.id, test_company.id,
            DailyReportReopen(reopen_reason="testing reopen order"), _ctx(),
        )

    # Sanity: the latest day (no later report exists) can be reopened.
    reopened = await svc.reopen(
        day2.id, test_company.id,
        DailyReportReopen(reopen_reason="testing reopen order"), _ctx(),
    )
    assert reopened.status == ReportStatus.DRAFT
